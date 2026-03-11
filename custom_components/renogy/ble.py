"""BLE communication module for Renogy devices."""

import asyncio
import importlib
import logging
import traceback
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, Callable, Optional, cast

try:
    from bleak import BleakClient, BleakError
except ImportError:
    # Test environments may stub bleak without exposing BleakClient.
    class BleakClient:  # type: ignore[no-redef]
        """Fallback BleakClient placeholder for import-time compatibility."""

    from bleak import BleakError
try:
    from bleak_retry_connector import establish_connection
except ImportError:
    establish_connection = None

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
    DeviceType,
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

# Check if Shunt300 support is available in the library.
try:
    renogy_ble_shunt: ModuleType | None = importlib.import_module("renogy_ble.shunt")
except ImportError:
    renogy_ble_shunt = None

if renogy_ble_shunt is not None:
    shunt_client_class = getattr(renogy_ble_shunt, "ShuntBleClient", None)
else:
    shunt_client_class = None

# Check if inverter support is available in the library.
try:
    renogy_ble_inverter: ModuleType | None = importlib.import_module(
        "renogy_ble.inverter"
    )
except ImportError:
    renogy_ble_inverter = None

if renogy_ble_inverter is not None:
    inverter_client_class = getattr(renogy_ble_inverter, "InverterBleClient", None)
else:
    inverter_client_class = None

LOAD_CONTROL_REGISTER = getattr(renogy_ble_module, "LOAD_CONTROL_REGISTER", 0x010A)


class RenogyActiveBluetoothCoordinator(
    ActiveBluetoothDataUpdateCoordinator[dict[str, Any]]
):
    """Class to manage fetching Renogy BLE data via active connections."""

    _global_connection_lock: asyncio.Lock | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        *,
        address: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        device_type: str = DEFAULT_DEVICE_TYPE,
        device_data_callback: Optional[Callable[[RenogyBLEDevice], None]] = None,
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
        self.device: Optional[RenogyBLEDevice] = None
        self.scan_interval = scan_interval
        self.device_type = device_type
        self.last_poll_time: Optional[datetime] = None
        self.device_data_callback = device_data_callback
        self.logger.debug(
            "Initialized coordinator for %s as %s with %ss interval",
            address,
            device_type,
            scan_interval,
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
        self._startup_time = (
            datetime.now()
        )  # Track initialization time for startup stabilization

        if RenogyActiveBluetoothCoordinator._global_connection_lock is None:
            RenogyActiveBluetoothCoordinator._global_connection_lock = asyncio.Lock()

    def _build_ble_client_for_type(self, device_type: str) -> RenogyBleClient:
        """Build a BLE client suitable for the configured device type."""
        scanner = bluetooth.async_get_scanner(self.hass)
        if device_type == DeviceType.SHUNT300.value and shunt_client_class is not None:
            return cast(RenogyBleClient, shunt_client_class())

        if device_type == DeviceType.SHUNT300.value:
            self.logger.warning(
                "ShuntBleClient not available in installed renogy-ble; "
                "falling back to RenogyBleClient for %s",
                self.address,
            )
        return RenogyBleClient(scanner=scanner)

    def _build_ble_client_for_type(self, device_type: str) -> RenogyBleClient:
        """Build a BLE client suitable for the configured device type."""
        scanner = bluetooth.async_get_scanner(self.hass)
        if device_type == DeviceType.SHUNT300.value and shunt_client_class is not None:
            return cast(RenogyBleClient, shunt_client_class())

        if device_type == DeviceType.SHUNT300.value:
            self.logger.warning(
                "ShuntBleClient not available in installed renogy-ble; "
                "falling back to RenogyBleClient for %s",
                self.address,
            )
        return RenogyBleClient(scanner=scanner)

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
            self.device.device_type == DeviceType.SHUNT300.value
            and shunt_client_class is not None
            and not isinstance(self._ble_client, shunt_client_class)
        ):
            self.logger.debug(
                "Switching BLE client to Smart Shunt handler for %s",
                service_info.address,
            )
            self._ble_client = cast(RenogyBleClient, shunt_client_class())

        return self.device

    @callback
    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        last_poll: float | None,
    ) -> bool:
        """Determine if device needs polling based on time since last poll."""
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

    async def _read_device_data(self, service_info: BluetoothServiceInfoBleak) -> bool:
        """Read data from a Renogy BLE device using active connection."""
        global_lock = RenogyActiveBluetoothCoordinator._global_connection_lock
        if global_lock is None:
            global_lock = asyncio.Lock()
            RenogyActiveBluetoothCoordinator._global_connection_lock = global_lock

        async with global_lock:
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

                    # Check if this is an inverter - use custom reading logic
                    if self.device_type == DeviceType.INVERTER.value:
                        self.logger.debug("Using inverter-specific BLE reading")
                        try:
                            success = await self._read_inverter_data(service_info)
                            error = (
                                None if success else Exception("Inverter read failed")
                            )
                        except Exception as err:
                            success = False
                            error = err
                            self.logger.debug(
                                "Inverter read failed for %s: %s",
                                device.address,
                                err,
                            )
                    else:
                        # Use standard renogy_ble library for controllers/DCC
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

                    # Shunt reads can fail transiently (e.g.,
                    # characteristic discovery races)
                    # even when the device is still healthy.
                    # Keep last-known values available
                    # instead of flipping entities to unavailable
                    # on single read failures.
                    if (
                        self.device_type == DeviceType.SHUNT300.value
                        and not success
                        and device.parsed_data
                    ):
                        self.logger.debug(
                            "Shunt read failed for %s, using cached data and "
                            "preserving availability",
                            device.address,
                        )
                        device.update_availability(True, None)
                        self.last_update_success = True
                        success = True

                    # Update coordinator data if successful
                    if success and device.parsed_data:
                        # Enrich Shunt data with metadata fields for diagnostic sensors
                        if self.device_type == DeviceType.SHUNT300.value:
                            shunt_data = device.parsed_data

                            # Add metadata fields if not already present
                            if "decode_confidence" not in shunt_data:
                                shunt_data["decode_confidence"] = "HIGH"
                            if "reading_verified" not in shunt_data:
                                shunt_data["reading_verified"] = True
                            if "status_source" not in shunt_data:
                                shunt_data["status_source"] = "derived_current"
                            if "energy_source" not in shunt_data:
                                shunt_data["energy_source"] = (
                                    "decoded"
                                    if shunt_data.get("shunt_energy") not in (None, 0)
                                    else "estimated_soc_capacity_1.28kWh"
                                )
                            if "verbose" not in shunt_data:
                                shunt_data["verbose"] = "0"

                            # Calculate estimated energy from SOC if available
                            if shunt_data.get("shunt_soc") is not None:
                                soc = float(shunt_data["shunt_soc"])
                                shunt_data["estimated_energy_kwh"] = round(
                                    (soc / 100.0) * 1.28, 3
                                )

                        self.data = dict(device.parsed_data)
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

        global_lock = RenogyActiveBluetoothCoordinator._global_connection_lock
        if global_lock is None:
            global_lock = asyncio.Lock()
            RenogyActiveBluetoothCoordinator._global_connection_lock = global_lock

        async with global_lock:
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
        # Don't mark as unavailable if we've successfully polled recently
        # (device disconnects after active reads, which is normal)
        if self.last_update_success and self.last_poll_time:
            time_since_poll = (datetime.now() - self.last_poll_time).total_seconds()
            if time_since_poll < self.scan_interval * 2:
                self.logger.debug(
                    "Device %s BLE unavailable but last poll was %ds ago (successful), "
                    "keeping status",
                    service_info.address,
                    time_since_poll,
                )
                return

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

    def _crc16_modbus(self, data: bytes) -> int:
        """Calculate Modbus CRC-16."""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    async def _read_inverter_data(
        self, service_info: BluetoothServiceInfoBleak
    ) -> bool:
        """Read data from Renogy inverter using renogy-ble public API only."""
        device = self.device
        if not device or inverter_client_class is None:
            self.logger.error("Inverter client class not available or device missing.")
            return False

        try:
            # Use the upstream renogy-ble inverter client for all BLE/Modbus operations
            try:
                inverter_client = inverter_client_class(
                    scanner=bluetooth.async_get_scanner(self.hass)
                )
            except TypeError:
                inverter_client = inverter_client_class()

            read_result = await inverter_client.read_device(device)
            if read_result.success and read_result.parsed_data:
                device.parsed_data = dict(read_result.parsed_data)
                self.logger.debug("Parsed inverter data: %s", device.parsed_data)
                return True
            else:
                self.logger.warning("Inverter read_device did not return data.")
                return False
        except Exception as e:
            self.logger.error(
                "Error reading inverter data via renogy-ble: %s", e, exc_info=True
            )
            return False

    async def async_write_register(self, register: int, value: int) -> bool:
        """
        Write a single register value to the inverter using renogy-ble public API only.
        """
        if not self.device or inverter_client_class is None:
            self.logger.error(
                "Cannot write register: inverter client or device missing."
            )
            return False

        try:
            try:
                inverter_client = inverter_client_class(
                    scanner=bluetooth.async_get_scanner(self.hass)
                )
            except TypeError:
                inverter_client = inverter_client_class()

            write_register_fn = getattr(inverter_client, "write_register", None)
            if not callable(write_register_fn):
                self.logger.error(
                    "write_register method not available in InverterBleClient. "
                    "Please update renogy-ble library."
                )
                return False

            success = await write_register_fn(self.device, register, value)
            if success:
                await self.async_request_refresh()
            return success
        except Exception as e:
            self.logger.error(
                "Error writing register %s via renogy-ble: %s", hex(register), e
            )
            return False
