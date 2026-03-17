"""BLE communication module for Renogy devices."""

from __future__ import annotations

import asyncio
import importlib
import logging
import traceback
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, cast

from bleak import BleakClient, BleakError
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from renogy_ble import ble as renogy_ble_module
from renogy_ble.ble import RenogyBleClient, RenogyBLEDevice, clean_device_name

from .const import (
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHUNT_CONNECTION_MODE,
    DeviceType,
    ShuntConnectionMode,
)
from .device_name import detect_device_type_from_ble_name, has_real_device_name

# Check if write_register is available in the library.
try:
    renogy_ble_ble: ModuleType | None = importlib.import_module("renogy_ble.ble")
except ImportError:
    renogy_ble_ble = None

if renogy_ble_ble is not None:
    create_modbus_write_request = getattr(
        renogy_ble_ble, "create_modbus_write_request", None
    )
    HAS_WRITE_SUPPORT = create_modbus_write_request is not None
else:
    create_modbus_write_request = None
    HAS_WRITE_SUPPORT = False

try:
    renogy_ble_shunt: ModuleType | None = importlib.import_module("renogy_ble.shunt")
except ImportError:
    renogy_ble_shunt = None

if renogy_ble_shunt is not None:
    shunt_client_class = getattr(renogy_ble_shunt, "ShuntBleClient", None)
    shunt_find_valid_payload_window = getattr(
        renogy_ble_shunt, "_find_valid_payload_window", None
    )
    shunt_expected_payload_length = getattr(
        renogy_ble_shunt, "SHUNT_EXPECTED_PAYLOAD_LENGTH", None
    )
    shunt_notify_char_uuid = getattr(
        renogy_ble_shunt,
        "SHUNT_NOTIFY_CHAR_UUID",
        "0000c411-0000-1000-8000-00805f9b34fb",
    )
else:
    shunt_client_class = None
    shunt_find_valid_payload_window = None
    shunt_expected_payload_length = None
    shunt_notify_char_uuid = "0000c411-0000-1000-8000-00805f9b34fb"

LOAD_CONTROL_REGISTER = getattr(renogy_ble_module, "LOAD_CONTROL_REGISTER", 0x010A)
SHUNT_RECONNECT_DELAY_SECONDS = 10
SHUNT_FORCE_UPDATE_INTERVAL_SECONDS = 300
SHUNT_AUTO_FALLBACK_FAILURES = 3


class RenogyActiveBluetoothCoordinator(
    ActiveBluetoothDataUpdateCoordinator[dict[str, Any]]
):
    """Class to manage fetching Renogy BLE data via active connections."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        address: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        device_type: str = DEFAULT_DEVICE_TYPE,
        shunt_connection_mode: str = DEFAULT_SHUNT_CONNECTION_MODE,
        device_data_callback: Callable[[RenogyBLEDevice], Awaitable[None]]
        | None = None,
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_device,
            mode=BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.device: RenogyBLEDevice | None = None
        self.scan_interval = scan_interval
        self.shunt_connection_mode = shunt_connection_mode
        self.device_type = device_type
        self.last_poll_time: datetime | None = None
        self.device_data_callback = device_data_callback
        self.logger.debug(
            "Initialized coordinator for %s as %s with %ss interval (%s shunt mode)",
            address,
            device_type,
            scan_interval,
            shunt_connection_mode,
        )

        self._shunt_listener_task: asyncio.Task[Any] | None = None
        self._last_sustained_shunt_push = 0.0
        self._last_sustained_shunt_data: dict[str, Any] = {}
        self._shunt_listener_failures = 0
        self._shunt_listener_last_success = 0.0
        self._shunt_auto_fallback_active = False
        self._shunt_energy_client = (
            shunt_client_class() if shunt_client_class is not None else None
        )
        self._ble_client = self._build_ble_client_for_type(device_type)

        # Add required properties for Home Assistant CoordinatorEntity compatibility
        self.last_update_success = True
        self._update_listeners: list[Callable[[], None]] = []
        self.update_interval = timedelta(seconds=scan_interval)
        self._unsub_refresh = None
        self._request_refresh_task = None

        # Add connection lock to prevent multiple concurrent connections
        self._connection_lock = asyncio.Lock()
        self._connection_in_progress = False

    def _build_ble_client_for_type(self, device_type: str) -> RenogyBleClient:
        """Build a BLE client suitable for the configured device type."""
        scanner = bluetooth.async_get_scanner(self.hass)
        if (
            self._uses_intermittent_shunt_reads(device_type)
            and shunt_client_class is not None
        ):
            return cast(RenogyBleClient, shunt_client_class())

        if self._uses_intermittent_shunt_reads(device_type):
            self.logger.warning(
                "ShuntBleClient not available in installed renogy-ble; "
                "falling back to RenogyBleClient for %s",
                self.address,
            )
        return RenogyBleClient(scanner=scanner)

    def _uses_sustained_shunt_listener(self, device_type: str | None = None) -> bool:
        """Return whether this coordinator should keep a sustained shunt listener."""
        resolved_type = device_type or self.device_type
        if self._shunt_auto_fallback_active:
            return False
        return (
            resolved_type == DeviceType.SHUNT300.value
            and self.shunt_connection_mode
            in {
                ShuntConnectionMode.SUSTAINED.value,
                ShuntConnectionMode.AUTO.value,
            }
        )

    def _uses_intermittent_shunt_reads(self, device_type: str | None = None) -> bool:
        """Return whether this coordinator should use intermittent shunt reads."""
        resolved_type = device_type or self.device_type
        if self._shunt_auto_fallback_active:
            return resolved_type == DeviceType.SHUNT300.value
        return (
            resolved_type == DeviceType.SHUNT300.value
            and self.shunt_connection_mode == ShuntConnectionMode.INTERMITTENT.value
        )

    def _handle_shunt_listener_failure(self, err: Exception) -> None:
        """Track sustained shunt listener failures and auto-fallback when needed."""
        self._shunt_listener_failures += 1
        if (
            self.shunt_connection_mode == ShuntConnectionMode.AUTO.value
            and self._shunt_listener_failures >= SHUNT_AUTO_FALLBACK_FAILURES
        ):
            self._shunt_auto_fallback_active = True
            self.logger.warning(
                "Sustained shunt listener failed %s times for %s; "
                "falling back to intermittent polling.",
                self._shunt_listener_failures,
                self.address,
            )
            if shunt_client_class is not None:
                self._ble_client = cast(RenogyBleClient, shunt_client_class())

    @property
    def device_type(self) -> str:
        """Get the device type from configuration."""
        return self._device_type

    @device_type.setter
    def device_type(self, value: str) -> None:
        """Set the device type."""
        self._device_type = value

    async def async_request_refresh(self) -> None:
        """Request a refresh."""
        self.logger.debug("Manual refresh requested for device %s", self.address)

        if self._uses_sustained_shunt_listener():
            self.logger.debug(
                "Skipping refresh for sustained shunt %s; listener owns updates",
                self.address,
            )
            return

        # If a connection is already in progress, don't start another one
        if self._connection_in_progress:
            self.logger.debug(
                "Connection already in progress, skipping refresh request"
            )
            return

        # Get the last available service info for this device
        service_info = bluetooth.async_last_service_info(self.hass, self.address)
        if not service_info:
            self.logger.error(
                "No service info available for device %s. Ensure device is within "
                "range and powered on.",
                self.address,
            )
            self.last_update_success = False
            return

        try:
            await self._async_poll_device(service_info)
            self.async_update_listeners()
        except Exception as err:
            self.last_update_success = False
            error_traceback = traceback.format_exc()
            self.logger.debug(
                "Error refreshing device %s: %s\n%s",
                self.address,
                str(err),
                error_traceback,
            )
            if self.device:
                self.device.update_availability(False, err)

    def async_add_listener(
        self, update_callback: Callable[[], None], context: Any = None
    ) -> Callable[[], None]:
        """Listen for data updates."""
        if update_callback not in self._update_listeners:
            self._update_listeners.append(update_callback)

        def remove_listener() -> None:
            """Remove update callback."""
            if update_callback in self._update_listeners:
                self._update_listeners.remove(update_callback)

        return remove_listener

    def async_update_listeners(self) -> None:
        """Update all registered listeners."""
        for update_callback in self._update_listeners:
            update_callback()

    def _schedule_refresh(self) -> None:
        """Schedule a refresh with the update interval."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        # Schedule the next refresh based on our scan interval
        self._unsub_refresh = async_track_time_interval(
            self.hass, self._handle_refresh_interval, self.update_interval
        )
        self.logger.debug("Scheduled next refresh in %s seconds", self.scan_interval)

    async def _handle_refresh_interval(self, _now=None):
        """Handle a refresh interval occurring."""
        self.logger.debug("Regular interval refresh for %s", self.address)
        await self.async_request_refresh()

    def async_start(self) -> Callable[[], None]:
        """Start polling."""
        self.logger.debug("Starting polling for device %s", self.address)

        def _unsub() -> None:
            """Unsubscribe from updates."""
            if self._unsub_refresh:
                self._unsub_refresh()
                self._unsub_refresh = None

        _unsub()  # Cancel any previous subscriptions

        if self._uses_sustained_shunt_listener():
            create_task = getattr(self.hass, "async_create_background_task", None)
            if callable(create_task):
                self._shunt_listener_task = create_task(
                    self._shunt_notification_loop(),
                    name=f"renogy_shunt_{self.address}",
                )
            else:
                self._shunt_listener_task = self.hass.async_create_task(
                    self._shunt_notification_loop()
                )
            return _unsub

        # We use the active update coordinator's start method
        # which already handles the bluetooth subscriptions
        result = super().async_start()

        # Schedule regular refreshes at our configured interval
        self._schedule_refresh()

        # Perform an initial refresh to get data as soon as possible
        self.hass.async_create_task(self.async_request_refresh())

        return result

    def _async_cancel_bluetooth_subscription(self) -> None:
        """Cancel the bluetooth subscription."""
        if hasattr(self, "_unsubscribe_bluetooth") and self._unsubscribe_bluetooth:
            self._unsubscribe_bluetooth()
            self._unsubscribe_bluetooth = None

    def async_stop(self) -> None:
        """Stop polling."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        if self._shunt_listener_task is not None:
            self._shunt_listener_task.cancel()
            self._shunt_listener_task = None

        self._async_cancel_bluetooth_subscription()

        # Clean up any other resources that might need to be released
        self._update_listeners = []

    def _update_device_from_service_info(
        self, service_info: BluetoothServiceInfoBleak
    ) -> RenogyBLEDevice:
        """Ensure the device instance is updated from Bluetooth service info."""
        detected_type = detect_device_type_from_ble_name(
            service_info.name, self.device_type
        )
        if self.device_type != detected_type:
            self.logger.debug(
                "Detected %s device from BLE name: %s",
                detected_type,
                service_info.name,
            )
            self.device_type = detected_type

        if not self.device:
            self.logger.debug(
                "Creating new RenogyBLEDevice for %s as %s",
                service_info.address,
                detected_type,
            )
            self.device = RenogyBLEDevice(
                service_info.device,
                service_info.advertisement.rssi,
                device_type=detected_type,
            )
        else:
            old_name = self.device.name
            self.device.ble_device = service_info.device
            if has_real_device_name(service_info.name):
                cleaned_name = clean_device_name(service_info.name)
                if old_name != cleaned_name:
                    self.device.name = cleaned_name
                    self.logger.debug(
                        "Updated device name from '%s' to '%s'",
                        old_name,
                        cleaned_name,
                    )

            self.device.rssi = (
                service_info.advertisement.rssi
                if service_info.advertisement
                and service_info.advertisement.rssi is not None
                else service_info.device.rssi
            )

            if self.device.device_type != self.device_type:
                self.logger.debug(
                    "Updating device type from '%s' to '%s'",
                    self.device.device_type,
                    self.device_type,
                )
                self.device.device_type = self.device_type

        if (
            self._uses_intermittent_shunt_reads(self.device.device_type)
            and shunt_client_class is not None
            and not isinstance(self._ble_client, shunt_client_class)
        ):
            self.logger.debug(
                "Switching BLE client to Smart Shunt handler for %s",
                service_info.address,
            )
            self._ble_client = cast(RenogyBleClient, shunt_client_class())
        elif self._uses_sustained_shunt_listener(self.device.device_type) and (
            shunt_client_class is None
            or isinstance(self._ble_client, shunt_client_class)
        ):
            self.logger.debug(
                "Switching BLE client to generic handler for sustained shunt %s",
                service_info.address,
            )
            self._ble_client = RenogyBleClient(
                scanner=bluetooth.async_get_scanner(self.hass)
            )

        return self.device

    @callback
    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        last_poll: float | None,
    ) -> bool:
        """Determine if device needs polling based on time since last poll."""
        if self._uses_sustained_shunt_listener():
            return False

        # Only poll if hass is running and device is connectable
        if self.hass.state != CoreState.running:
            return False

        # Check if we have a connectable device
        connectable_device = bluetooth.async_ble_device_from_address(
            self.hass, service_info.device.address, connectable=True
        )
        if not connectable_device:
            self.logger.warning(
                "No connectable device found for %s", service_info.address
            )
            return False

        # If a connection is already in progress, don't start another one
        if self._connection_in_progress:
            self.logger.debug("Connection already in progress, skipping poll")
            return False

        # If we've never polled or it's been longer than the scan interval, poll
        if last_poll is None:
            self.logger.debug("First poll for device %s", service_info.address)
            return True

        # Check if enough time has elapsed since the last poll
        time_since_poll = datetime.now().timestamp() - last_poll
        should_poll = time_since_poll >= self.scan_interval

        if should_poll:
            self.logger.debug(
                "Time to poll device %s after %.1fs",
                service_info.address,
                time_since_poll,
            )

        return should_poll

    def _process_sustained_shunt_notification(self, data: bytes) -> None:
        """Parse and publish one sustained Smart Shunt notification payload."""
        if (
            shunt_find_valid_payload_window is None
            or shunt_expected_payload_length is None
        ):
            return

        maybe_payload = shunt_find_valid_payload_window(
            data, shunt_expected_payload_length
        )
        if maybe_payload is None:
            return

        raw_payload, parsed_data = maybe_payload
        now = self.hass.loop.time()
        if self._shunt_energy_client is not None:
            charged_kwh, discharged_kwh = (
                self._shunt_energy_client._integrate_energy_totals(
                    device_address=self.address,
                    power_w=parsed_data.get("shunt_power"),
                    now_ts=now,
                )
            )
            parsed_data["energy_charged_total"] = round(charged_kwh, 3)
            parsed_data["energy_discharged_total"] = round(discharged_kwh, 3)
        parsed_data["raw_payload"] = raw_payload.hex()
        self._shunt_listener_failures = 0
        self._shunt_listener_last_success = now

        changed = any(
            parsed_data.get(key) != self._last_sustained_shunt_data.get(key)
            for key in (
                "shunt_voltage",
                "shunt_current",
                "shunt_power",
                "shunt_soc",
                "energy_charged_total",
                "energy_discharged_total",
            )
        )
        stale = (
            now - self._last_sustained_shunt_push >= SHUNT_FORCE_UPDATE_INTERVAL_SECONDS
        )
        # Keep the recovery path alive after a transient listener failure even
        # when the first restored payload matches the previous values.
        if not changed and not stale and self.last_update_success:
            return

        if self.device is not None:
            existing_data = (
                dict(self.device.parsed_data)
                if isinstance(self.device.parsed_data, dict)
                else {}
            )
            existing_data.update(parsed_data)
            self.device.parsed_data = existing_data
            self.device.update_availability(True, None)

        current_data = dict(self.data) if isinstance(self.data, dict) else {}
        current_data.update(parsed_data)
        self.data = current_data
        self.last_update_success = True
        self._last_sustained_shunt_data = dict(parsed_data)
        self._last_sustained_shunt_push = now
        self.hass.loop.call_soon_threadsafe(self.async_update_listeners)

    async def _shunt_notification_loop(self) -> None:
        """Maintain a sustained notification listener for Smart Shunt devices."""
        while True:
            if self._shunt_auto_fallback_active:
                return
            client: Any = None
            try:
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.address
                )
                if not service_info:
                    self.logger.debug(
                        "No Smart Shunt service info available for %s; retrying in %ss",
                        self.address,
                        SHUNT_RECONNECT_DELAY_SECONDS,
                    )
                    await asyncio.sleep(SHUNT_RECONNECT_DELAY_SECONDS)
                    continue

                self._update_device_from_service_info(service_info)
                client = await establish_connection(
                    BleakClient,
                    service_info.device,
                    self.device.name if self.device is not None else self.address,
                    max_attempts=3,
                )

                def notification_handler(
                    _sender: BleakGATTCharacteristic | int | str, data: bytearray
                ) -> None:
                    self._process_sustained_shunt_notification(bytes(data))

                await client.start_notify(shunt_notify_char_uuid, notification_handler)
                while getattr(client, "is_connected", True):
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                if client is not None:
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                raise
            except Exception as err:
                self.last_update_success = False
                if self.device is not None:
                    self.device.update_availability(False, err)
                self.hass.loop.call_soon_threadsafe(self.async_update_listeners)
                self._handle_shunt_listener_failure(err)
                self.logger.debug(
                    "Smart Shunt listener error for %s: %s",
                    self.address,
                    err,
                )
            finally:
                if client is not None:
                    try:
                        await client.stop_notify(shunt_notify_char_uuid)
                    except Exception:
                        pass
                    try:
                        await client.disconnect()
                    except Exception:
                        pass

            if self._shunt_auto_fallback_active:
                return

            await asyncio.sleep(SHUNT_RECONNECT_DELAY_SECONDS)

    async def _read_device_data(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Read data from a Renogy BLE device using active connection."""
        async with self._connection_lock:
            try:
                self._connection_in_progress = True
                success = False
                error: Exception | None = None
                device = self._update_device_from_service_info(service_info)
                self.logger.debug(
                    "Polling %s device: %s (%s)",
                    device.device_type,
                    device.name,
                    device.address,
                )

                try:
                    read_result = await self._ble_client.read_device(device)
                except (BleakError, asyncio.TimeoutError) as err:
                    success = False
                    error = err
                    self.logger.debug(
                        "BLE read failed for %s: %s",
                        device.address,
                        err,
                    )
                else:
                    success = read_result.success
                    error = read_result.error
                    if error is not None and not isinstance(error, Exception):
                        error = Exception(str(error))

                # Always update the device availability and last_update_success
                device.update_availability(success, error)
                self.last_update_success = success

                # Update coordinator data if successful
                if success and device.parsed_data:
                    updated = dict(device.parsed_data)
                    if device.device_type == DeviceType.INVERTER.value and isinstance(
                        self.data, dict
                    ):
                        merged = dict(self.data)
                        merged.update(updated)
                        self.data = merged
                    else:
                        self.data = updated
                    self.logger.debug("Updated coordinator data: %s", self.data)

                return success
            finally:
                self._connection_in_progress = False

    async def async_set_load_state(self, state: bool) -> bool:
        """Set the DC load on/off."""
        if self._connection_in_progress:
            self.logger.debug("Connection already in progress, skipping load write")
            return False

        service_info = bluetooth.async_last_service_info(self.hass, self.address)
        if not service_info:
            self.logger.error(
                "No service info available for device %s. Ensure device is within "
                "range and powered on.",
                self.address,
            )
            return False

        async with self._connection_lock:
            self._connection_in_progress = True
            try:
                device = self._update_device_from_service_info(service_info)
                value = 1 if state else 0
                write_single_register = getattr(
                    self._ble_client, "write_single_register", None
                )
                if write_single_register is None:
                    self.logger.error(
                        "Renogy BLE library does not support write_single_register"
                    )
                    device.update_availability(False, None)
                    self.last_update_success = False
                    return False

                write_result = await write_single_register(
                    device, LOAD_CONTROL_REGISTER, value
                )
                device.update_availability(write_result.success, write_result.error)
                self.last_update_success = write_result.success

                if write_result.success:
                    load_state = "on" if state else "off"
                    if device.parsed_data is not None:
                        device.parsed_data["load_status"] = load_state
                    if isinstance(self.data, dict):
                        self.data["load_status"] = load_state
                    else:
                        self.data = {"load_status": load_state}
                    self.async_update_listeners()

                return write_result.success
            finally:
                self._connection_in_progress = False

    async def _async_poll_device(
        self, service_info: BluetoothServiceInfoBleak
    ) -> dict[str, Any]:
        """Poll the device and return parsed data."""
        if self._uses_sustained_shunt_listener():
            return self.data if isinstance(self.data, dict) else {}

        # If a connection is already in progress, don't start another one
        if self._connection_in_progress:
            self.logger.debug("Connection already in progress, skipping poll")
            return self.data if isinstance(self.data, dict) else {}

        self.last_poll_time = datetime.now()
        self.logger.debug(
            "Polling device: %s (%s)", service_info.name, service_info.address
        )

        # Read device data using service_info and Home Assistant's Bluetooth API
        success = await self._read_device_data(service_info)

        if success and self.device and self.device.parsed_data:
            # Log the parsed data for debugging
            self.logger.debug("Parsed data: %s", self.device.parsed_data)

            # Call the callback if available
            if self.device_data_callback:
                try:
                    await self.device_data_callback(self.device)
                except Exception as e:
                    self.logger.error("Error in device data callback: %s", str(e))

            # Update all listeners after successful data acquisition
            return dict(self.device.parsed_data)

        else:
            self.logger.info("Failed to retrieve data from %s", service_info.address)
            self.last_update_success = False
            return self.data if isinstance(self.data, dict) else {}

    @callback
    def _async_handle_unavailable(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""
        self.logger.info("Device %s is no longer available", service_info.address)
        self.last_update_success = False
        self.async_update_listeners()

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        # Update RSSI if device exists
        if self.device:
            self.device.rssi = service_info.advertisement.rssi
            self.device.last_seen = datetime.now()

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register value to the device.

        Args:
            register: Register address to write (e.g., 0xE004 for battery type)
            value: 16-bit value to write

        Returns:
            True if write was successful, False otherwise
        """
        if not self.device:
            self.logger.error("Cannot write register: no device connected")
            return False

        # Check if write support is available in renogy-ble library
        if not HAS_WRITE_SUPPORT:
            self.logger.error(
                "Write support not available in renogy-ble library. "
                "Please update to a version with write_register support."
            )
            return False

        # Try to use the library's write method if available.
        write_register_fn = getattr(self._ble_client, "write_register", None)
        if callable(write_register_fn):
            write_register = cast(
                Callable[[RenogyBLEDevice, int, int], Awaitable[bool]],
                write_register_fn,
            )
            try:
                success = await write_register(self.device, register, value)
                if success:
                    # Trigger a refresh to update the new value
                    await self.async_request_refresh()
                return success
            except Exception as e:
                self.logger.error("Error writing register %s: %s", hex(register), e)
                return False
        else:
            self.logger.error(
                "write_register method not available in RenogyBleClient. "
                "Please update renogy-ble library."
            )
            return False
