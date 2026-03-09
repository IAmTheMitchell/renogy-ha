"""BLE helper for Renogy Shunt 300 devices.

The stock `renogy-ble` library does not currently include the Smart Shunt
protocol. This module adds a tiny client that understands the notification-only
payload the shunt broadcasts so the integration can surface useful sensors.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from renogy_ble.ble import RenogyBLEDevice, RenogyBleReadResult

_LOGGER = logging.getLogger(__name__)

# The Smart Shunt notifies on this characteristic without requiring writes.
SHUNT_NOTIFY_CHAR_UUID = "0000c411-0000-1000-8000-00805f9b34fb"

# Based on empirical captures from https://github.com/TySweeden/renogy-data-capture
# the shunt sends a 110-byte frame every few seconds.
SHUNT_EXPECTED_PAYLOAD_LENGTH = 110

KEY_SHUNT_VOLTAGE = "shunt_voltage"
KEY_SHUNT_CURRENT = "shunt_current"
KEY_SHUNT_POWER = "shunt_power"
KEY_SHUNT_SOC = "shunt_soc"
KEY_SHUNT_ENERGY = "shunt_energy"


def _bytes_to_number(
    payload: bytes,
    offset: int,
    length: int,
    *,
    signed: bool = False,
    scale: float = 1.0,
    decimals: int | None = None,
) -> float | int | None:
    """Extract a numeric value from the payload.

    Returns None when the payload is shorter than the requested slice so callers
    can safely skip absent fields.
    """
    if len(payload) < offset + length:
        return None

    value = int.from_bytes(
        payload[offset : offset + length], byteorder="big", signed=signed
    )
    scaled = value * scale
    return round(scaled, decimals) if decimals is not None else scaled


def parse_shunt_payload(payload: bytes) -> dict[str, Any] | None:
    """Parse a raw Smart Shunt notification frame."""
    voltage = _bytes_to_number(payload, 25, 3, scale=0.001, decimals=2)
    starter_voltage = _bytes_to_number(payload, 30, 2, scale=0.001, decimals=2)
    current = _bytes_to_number(payload, 21, 3, signed=True, scale=0.001, decimals=2)
    power = (
        round(voltage * current, 2)
        if voltage is not None and current is not None
        else None
    )

    # State of charge is stored as 0.1% increments at byte offset 34.
    soc = _bytes_to_number(payload, 34, 2, scale=0.1, decimals=1)

    # Battery temperature appears at offset 66 in 0.1°C increments.
    battery_temp = _bytes_to_number(payload, 66, 2, scale=0.1, decimals=1)

    # Basic sanity filters to ignore corrupt frames (seen rarely as 1310V, etc.).
    if voltage is None or current is None or power is None:
        return None
    if voltage < 0 or voltage > 80:
        return None
    if abs(current) > 500:
        return None
    if abs(power) > 10000:
        return None
    if battery_temp is not None and (battery_temp < -40 or battery_temp > 100):
        battery_temp = None
    if soc is not None and (soc < 0 or soc > 200):
        soc = None

    parsed: dict[str, Any] = {
        KEY_SHUNT_VOLTAGE: voltage,
        KEY_SHUNT_CURRENT: current,
        KEY_SHUNT_POWER: power,
        KEY_SHUNT_SOC: soc,
        KEY_SHUNT_ENERGY: None,
        "starter_battery_voltage": starter_voltage,
        "battery_temperature": battery_temp,
    }

    return parsed


class ShuntBleClient:
    """Minimal BLE client that listens for Smart Shunt notifications."""

    def __init__(
        self,
        *,
        notify_char_uuid: str = SHUNT_NOTIFY_CHAR_UUID,
        expected_length: int = SHUNT_EXPECTED_PAYLOAD_LENGTH,
        max_notification_wait_time: float = 3.0,
        max_attempts: int = 3,
    ) -> None:
        self._notify_char_uuid = notify_char_uuid
        self._expected_length = expected_length
        self._max_notification_wait_time = max_notification_wait_time
        self._max_attempts = max_attempts
        self._last_energy_ts: float | None = None
        self._net_wh: float = 0.0

    async def read_device(self, device: RenogyBLEDevice) -> RenogyBleReadResult:
        """Connect, wait for a single notification frame, and parse it."""
        payload = bytearray()
        event = asyncio.Event()
        error: Exception | None = None
        success = False

        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                device.ble_device,
                device.name or device.address,
                max_attempts=self._max_attempts,
            )
        except (BleakError, asyncio.TimeoutError) as exc:
            _LOGGER.info("Failed to connect to Smart Shunt %s: %s", device.address, exc)
            return RenogyBleReadResult(False, dict(device.parsed_data), exc)

        try:
            _LOGGER.debug("Connected to Smart Shunt %s", device.address)

            def notification_handler(
                _sender: BleakGATTCharacteristic | int | str, data: bytearray
            ) -> None:
                payload.extend(data)
                event.set()

            await client.start_notify(self._notify_char_uuid, notification_handler)
            loop = asyncio.get_running_loop()
            start = loop.time()

            while len(payload) < self._expected_length:
                remaining = self._max_notification_wait_time - (loop.time() - start)
                if remaining <= 0:
                    raise asyncio.TimeoutError(
                        f"No shunt payload after {self._max_notification_wait_time}s"
                    )
                await asyncio.wait_for(event.wait(), remaining)
                event.clear()

            raw_payload = bytes(payload[: self._expected_length])
            parsed = parse_shunt_payload(raw_payload)

            if parsed:
                # Simple net energy integration (W * time) since coordinator start.
                now = asyncio.get_running_loop().time()
                if self._last_energy_ts is None:
                    self._last_energy_ts = now
                else:
                    dt_hours = (now - self._last_energy_ts) / 3600
                    # Ignore huge gaps to avoid runaway integration.
                    if 0 < dt_hours < 10 and parsed.get(KEY_SHUNT_POWER) is not None:
                        self._net_wh += float(parsed[KEY_SHUNT_POWER]) * dt_hours
                    self._last_energy_ts = now
                parsed[KEY_SHUNT_ENERGY] = round(self._net_wh / 1000, 3)

                parsed["raw_payload"] = raw_payload.hex()
                parsed["raw_words"] = [
                    int.from_bytes(
                        raw_payload[i * 2 : (i + 1) * 2], "big", signed=False
                    )
                    for i in range(len(raw_payload) // 2)
                ]
                device.parsed_data = parsed
                _LOGGER.debug(
                    "Raw shunt payload (%s bytes): %s",
                    len(raw_payload),
                    raw_payload.hex(),
                )
                _LOGGER.debug("Parsed shunt payload: %s", parsed)
                success = True
            else:
                error = RuntimeError("Empty shunt payload parsed")

            await client.stop_notify(self._notify_char_uuid)
        except asyncio.TimeoutError as exc:
            _LOGGER.info("Timed out waiting for Smart Shunt data: %s", exc)
            error = exc
        except (BleakError, Exception) as exc:  # noqa: BLE001
            _LOGGER.error("Error reading Smart Shunt data: %s", exc)
            error = exc
        finally:
            if client.is_connected:
                try:
                    await client.disconnect()
                    _LOGGER.debug("Disconnected from Smart Shunt %s", device.address)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.debug("Error disconnecting Smart Shunt: %s", exc)
                    if error is None:
                        error = exc

        return RenogyBleReadResult(success, dict(device.parsed_data), error)
