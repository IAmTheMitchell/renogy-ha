"""BLE communication module for Renogy devices."""

import asyncio
import importlib
import logging
import struct
import traceback
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, Awaitable, Callable, Optional, cast

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
    INVERTER_DEVICE_ID,
    INVERTER_INIT_UUID,
    INVERTER_MODES,
    INVERTER_NOTIFY_UUID,
    INVERTER_WRITE_UUID,
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
        self._startup_time = datetime.now()  # Track initialization time for startup stabilization

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

                    # Shunt reads can fail transiently (e.g., characteristic discovery races)
                    # even when the device is still healthy. Keep last-known values available
                    # instead of flipping entities to unavailable on single read failures.
                    if (
                        self.device_type == DeviceType.SHUNT300.value
                        and not success
                        and device.parsed_data
                    ):
                        self.logger.debug(
                            "Shunt read failed for %s, using cached data and preserving availability",
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
                    device.update_availability(
                        write_result.success, write_result.error
                    )
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
                    "Device %s BLE unavailable but last poll was %ds ago (successful), keeping status",
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
        """Read data from Renogy inverter using Modbus protocol over BLE."""
        device = self.device
        if not device:
            return False

        from .sensor import KEY_INVERTER_DEVICE_ID, KEY_INVERTER_MODEL

        cached_device_id = None
        cached_model = None
        if device.parsed_data:
            cached_device_id = device.parsed_data.get(KEY_INVERTER_DEVICE_ID)
            cached_model = device.parsed_data.get(KEY_INVERTER_MODEL)
        
        # Initialize parsed_data with cached values to preserve them across poll failures
        if not device.parsed_data:
            device.parsed_data = {}
        if cached_device_id is not None:
            device.parsed_data[KEY_INVERTER_DEVICE_ID] = cached_device_id
        if cached_model is not None:
            device.parsed_data[KEY_INVERTER_MODEL] = cached_model

        # Prefer upstream library support when it is available.
        if inverter_client_class is not None:
            try:
                try:
                    inverter_client = inverter_client_class(
                        scanner=bluetooth.async_get_scanner(self.hass)
                    )
                except TypeError:
                    inverter_client = inverter_client_class()

                read_result = await inverter_client.read_device(device)
                if read_result.success and read_result.parsed_data:
                    parsed_data = dict(read_result.parsed_data)

                    # Preserve cached static values if upstream read does not include them.
                    if (
                        cached_device_id is not None
                        and KEY_INVERTER_DEVICE_ID not in parsed_data
                    ):
                        parsed_data[KEY_INVERTER_DEVICE_ID] = cached_device_id
                    if cached_model is not None and KEY_INVERTER_MODEL not in parsed_data:
                        parsed_data[KEY_INVERTER_MODEL] = cached_model

                    device.parsed_data = parsed_data
                    return True
            except Exception as e:
                self.logger.debug(
                    "Upstream inverter client unavailable or failed, using local fallback: %s",
                    e,
                )

        try:
            # Log connection attempt
            self.logger.debug("Connecting to inverter %s", service_info.address)
            
            # Add startup delay to allow Bluetooth stack to stabilize (especially important during HA startup)
            time_since_startup = (datetime.now() - self._startup_time).total_seconds()
            startup_stabilization_time = 30  # Wait 30 seconds after startup for BLE stack to stabilize
            if time_since_startup < startup_stabilization_time:
                remaining_wait = int(startup_stabilization_time - time_since_startup)
                self.logger.debug(
                    "Delaying first inverter connection by %ds to allow Bluetooth stack to stabilize",
                    remaining_wait
                )
                await asyncio.sleep(remaining_wait)
            
            # Create client and establish connection with proper timeout handling.
            # Use bleak-retry-connector when available to align with habluetooth expectations.
            # Fall back to direct BleakClient connect if the dependency is unavailable.
            connectable_device = bluetooth.async_ble_device_from_address(
                self.hass, service_info.address, connectable=True
            )
            if connectable_device is None:
                self.logger.warning(
                    "No connectable BLE device found for inverter %s",
                    service_info.address,
                )
                return False

            client: BleakClient
            connection_name = service_info.name or service_info.address
            if establish_connection is not None:
                try:
                    client = await establish_connection(
                        BleakClient,
                        connectable_device,
                        connection_name,
                        max_attempts=2,
                    )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Connection timeout to inverter %s", service_info.address
                    )
                    return False
                except BleakError as e:
                    self.logger.warning("Connection error to inverter: %s", e)
                    return False
                except Exception as e:
                    self.logger.warning(
                        "Failed to establish retry connection to inverter: %s", e
                    )
                    return False
            else:
                client = BleakClient(service_info.address)
                try:
                    await asyncio.wait_for(client.connect(), timeout=20.0)
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "Connection timeout to inverter %s", service_info.address
                    )
                    return False
                except BleakError as e:
                    self.logger.warning("Connection error to inverter: %s", e)
                    return False
                except Exception as e:
                    self.logger.warning(
                        "Failed to establish connection to inverter: %s", e
                    )
                    return False
            
            if not client.is_connected:
                self.logger.warning("Failed to connect to inverter")
                return False

            self.logger.debug("Inverter connected successfully")
            await asyncio.sleep(0.5)  # Allow connection to fully stabilize before reading

            # Initialize - read from ffd4 characteristic
            try:
                init_data = await client.read_gatt_char(INVERTER_INIT_UUID)
                self.logger.debug("Inverter init data: %s", init_data.hex())
            except Exception as e:
                self.logger.debug("Inverter init read failed (may be normal): %s", e)

            # Prepare for notifications
            response_data = []
            response_event = asyncio.Event()

            def notification_handler(sender, data: bytes):
                nonlocal response_data
                self.logger.debug("Notification received from %s: %d bytes", sender, len(data))
                response_data.append(data)
                response_event.set()

            # Start notifications
            await client.start_notify(INVERTER_NOTIFY_UUID, notification_handler)
            await asyncio.sleep(1.0)  # Allow notification characteristic to stabilize (prevents first-attempt timeouts)

            # Build Modbus request to read main sensors (register 4000)
            # Start register: 4000 (validated from test script), Read 32 registers
            function_code = 3  # Read holding registers
            start_register = 4000
            register_count = 32

            payload = bytearray()
            payload.append(INVERTER_DEVICE_ID)  # Device ID (32)
            payload.append(function_code)
            payload += struct.pack('>H', start_register)  # Big-endian register
            payload += struct.pack('>H', register_count)  # Big-endian count
            
            # Calculate and append CRC (little-endian)
            crc = self._crc16_modbus(payload)
            payload += struct.pack('<H', crc)

            self.logger.debug("Sending Modbus request for 4000: %s", payload.hex())

            # Send request with retry logic for intermittent timeouts
            MAX_RETRIES = 2
            success = False
            for attempt in range(MAX_RETRIES):
                if attempt > 0:
                    # Clear and reset for retry
                    response_data.clear()
                    response_event.clear()
                    await asyncio.sleep(0.5)
                    self.logger.debug("Retrying Modbus request for 4000 (attempt %d/%d): %s", 
                                    attempt + 1, MAX_RETRIES, payload.hex())
                
                await client.write_gatt_char(INVERTER_WRITE_UUID, payload, response=False)
                
                try:
                    self.logger.debug("Waiting for inverter response (4000)... (attempt %d/%d)", 
                                    attempt + 1, MAX_RETRIES)
                    await asyncio.wait_for(response_event.wait(), timeout=10.0)
                    self.logger.debug("Response received for 4000")
                    success = True
                    break
                except asyncio.TimeoutError:
                    if attempt < MAX_RETRIES - 1:
                        self.logger.warning("Timeout waiting for inverter response (4000) - retrying...")
                    else:
                        self.logger.warning("Timeout waiting for inverter response (4000) after %d attempts", MAX_RETRIES)
            
            if not success:
                await client.disconnect()
                return False

            # Parse main sensor response
            parsed_data = {}
            if response_data:
                raw_response = b''.join(response_data)
                self.logger.debug("Inverter raw response (4000): %s", raw_response.hex())
                
                # Parse the Modbus response into sensor data
                parsed_data = self._parse_inverter_response(raw_response)

            # Now read load info from register 4408
            response_data.clear()
            response_event.clear()
            
            start_register_load = 4408
            register_count_load = 6  # Load Info: 6 registers
            
            payload_load = bytearray()
            payload_load.append(INVERTER_DEVICE_ID)
            payload_load.append(function_code)
            payload_load += struct.pack('>H', start_register_load)
            payload_load += struct.pack('>H', register_count_load)
            crc_load = self._crc16_modbus(payload_load)
            payload_load += struct.pack('<H', crc_load)
            
            self.logger.debug("Sending Modbus request for 4408: %s", payload_load.hex())
            
            await asyncio.sleep(0.3)  # Small delay between requests
            await client.write_gatt_char(INVERTER_WRITE_UUID, payload_load, response=False)
            
            try:
                self.logger.debug("Waiting for inverter response (4408)...")
                await asyncio.wait_for(response_event.wait(), timeout=10.0)
                self.logger.debug("Response received for 4408")
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for inverter response (4408) after 10s")
                # Continue even if second read fails
            
            # Parse load info response
            if response_data:
                raw_response_load = b''.join(response_data)
                self.logger.debug("Inverter raw response (4408): %s", raw_response_load.hex())
                load_data = self._parse_inverter_load_response(raw_response_load)
                if load_data:
                    parsed_data.update(load_data)

            # Read static values only when missing; keep cached values stable across polls
            if cached_device_id is None:
                response_data.clear()
                response_event.clear()

                payload_id = bytearray()
                payload_id.append(INVERTER_DEVICE_ID)
                payload_id.append(function_code)
                payload_id += struct.pack('>H', 4109)  # Device ID register
                payload_id += struct.pack('>H', 1)  # 1 register
                crc_id = self._crc16_modbus(payload_id)
                payload_id += struct.pack('<H', crc_id)

                self.logger.debug("Sending Modbus request for 4109: %s", payload_id.hex())

                await asyncio.sleep(0.3)
                await client.write_gatt_char(INVERTER_WRITE_UUID, payload_id, response=False)

                try:
                    self.logger.debug("Waiting for inverter response (4109)...")
                    await asyncio.wait_for(response_event.wait(), timeout=10.0)
                    self.logger.debug("Response received for 4109")
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout waiting for inverter response (4109) after 10s")

                if response_data:
                    raw_response_id = b''.join(response_data)
                    self.logger.debug("Inverter raw response (4109): %s", raw_response_id.hex())
                    device_id_data = self._parse_device_id_response(raw_response_id)
                    if device_id_data:
                        parsed_data.update(device_id_data)
            else:
                parsed_data[KEY_INVERTER_DEVICE_ID] = cached_device_id

            if cached_model is None:
                response_data.clear()
                response_event.clear()

                payload_model = bytearray()
                payload_model.append(INVERTER_DEVICE_ID)
                payload_model.append(function_code)
                payload_model += struct.pack('>H', 4311)  # Model register
                payload_model += struct.pack('>H', 8)  # 8 registers (16 bytes for ASCII)
                crc_model = self._crc16_modbus(payload_model)
                payload_model += struct.pack('<H', crc_model)

                self.logger.debug("Sending Modbus request for 4311: %s", payload_model.hex())

                await asyncio.sleep(0.3)
                await client.write_gatt_char(INVERTER_WRITE_UUID, payload_model, response=False)

                try:
                    self.logger.debug("Waiting for inverter response (4311)...")
                    await asyncio.wait_for(response_event.wait(), timeout=10.0)
                    self.logger.debug("Response received for 4311")
                except asyncio.TimeoutError:
                    self.logger.warning("Timeout waiting for inverter response (4311) after 10s")

                if response_data:
                    raw_response_model = b''.join(response_data)
                    self.logger.debug("Inverter raw response (4311): %s", raw_response_model.hex())
                    model_data = self._parse_model_response(raw_response_model)
                    if model_data:
                        parsed_data.update(model_data)
            else:
                parsed_data[KEY_INVERTER_MODEL] = cached_model
                
            # Ensure cached static values are always preserved in parsed_data
            # so diagnostic sensors never go unavailable between polls
            if cached_device_id is not None and KEY_INVERTER_DEVICE_ID not in parsed_data:
                parsed_data[KEY_INVERTER_DEVICE_ID] = cached_device_id
            if cached_model is not None and KEY_INVERTER_MODEL not in parsed_data:
                parsed_data[KEY_INVERTER_MODEL] = cached_model
                
            if parsed_data:
                device.parsed_data = parsed_data
                self.logger.debug("Parsed inverter data: %s", parsed_data)
                await client.disconnect()
                return True

            await client.disconnect()
            return False

        except Exception as e:
            error_msg = str(e)
            # Handle Bluetooth stack being shutdown during startup/HA initialization
            if "already shutdown" in error_msg.lower():
                self.logger.warning(
                    "Bluetooth stack not ready (shutdown/reinitializing). Will retry on next poll cycle: %s",
                    e
                )
            else:
                self.logger.error("Error reading inverter data: %s", e, exc_info=True)
            return False

    def _parse_inverter_response(self, data: bytes) -> dict[str, Any]:
        """Parse Modbus response from RIV1220PU inverter into sensor values.
        
        Reading 32 registers starting from 4000 (validated from test script):
        - Index 0 = Register 4000 (AC Input Voltage)
        - Index 1 = Register 4001 (AC Input Current)
        - Index 2 = Register 4002 (AC Output Voltage)
        - Index 3 = Register 4003 (AC Output Current)
        - Index 4 = Register 4004 (AC Output Frequency)
        - Index 5 = Register 4005 (Battery Voltage)
        - Index 6 = Register 4006 (Temperature)
        """
        from .sensor import (
            KEY_INVERTER_AC_CURRENT,
            KEY_INVERTER_AC_FREQUENCY,
            KEY_INVERTER_AC_VOLTAGE,
            KEY_INVERTER_BATTERY_VOLTAGE,
            KEY_INVERTER_INPUT_FREQUENCY,
            KEY_INVERTER_TEMPERATURE,
        )

        try:
            # Skip Modbus header (device ID, function, byte count)
            if len(data) < 5:
                self.logger.warning("Inverter response too short: %d bytes", len(data))
                return {}

            # Extract register values (big-endian 16-bit words)
            values = []
            # Start at byte 3 (after device ID, function code, byte count)
            for i in range(3, len(data) - 2, 2):  # Skip CRC at end
                if i + 1 < len(data):
                    value = struct.unpack('>H', data[i:i+2])[0]
                    values.append(value)

            self.logger.debug("Extracted %d register values", len(values))

            if len(values) < 7:
                self.logger.warning("Not enough register values: %d", len(values))
                return {}

            # Map register values to sensors (indices relative to start register 4000)
            # Based on validated test script discover_and_read_renogy_sensors.py
            parsed = {
                KEY_INVERTER_AC_VOLTAGE: values[2] * 0.1 if len(values) > 2 else 0,  # Reg 4002 (index 2) - AC output voltage
                KEY_INVERTER_AC_CURRENT: values[3] * 0.01 if len(values) > 3 else 0,  # Reg 4003 (index 3) - AC output current
                KEY_INVERTER_AC_FREQUENCY: values[4] * 0.01 if len(values) > 4 else 0,  # Reg 4004 (index 4) - AC output frequency
                KEY_INVERTER_BATTERY_VOLTAGE: values[5] * 0.1 if len(values) > 5 else 0,  # Reg 4005 (index 5) - Battery voltage
                KEY_INVERTER_TEMPERATURE: values[6] * 0.1 if len(values) > 6 else 0,  # Reg 4006 (index 6) - Temperature
                KEY_INVERTER_INPUT_FREQUENCY: values[9] * 0.01 if len(values) > 9 else 0,  # Reg 4009 (index 9) - Grid frequency
            }

            return parsed

        except Exception as e:
            self.logger.error("Error parsing inverter response: %s", e, exc_info=True)
            return {}

    def _parse_inverter_load_response(self, data: bytes) -> dict[str, Any]:
        """Parse Modbus response from register 4408 (Load Info) into sensor values."""
        from .sensor import (
            KEY_INVERTER_LOAD_ACTIVE_POWER,
            KEY_INVERTER_LOAD_APPARENT_POWER,
        )

        try:
            if len(data) < 5:
                self.logger.warning("Load response too short: %d bytes", len(data))
                return {}

            # Extract register values (big-endian 16-bit words)
            values = []
            for i in range(3, len(data) - 2, 2):  # Skip header and CRC
                if i + 1 < len(data):
                    value = struct.unpack('>H', data[i:i+2])[0]
                    values.append(value)

            self.logger.debug("Extracted %d load register values", len(values))

            if len(values) < 3:
                return {}

            # Map load values from register 4408:
            # Index 0 = Reg 4408 (load_current)
            # Index 1 = Reg 4409 (load_active_power)
            # Index 2 = Reg 4410 (load_apparent_power)
            parsed = {
                KEY_INVERTER_LOAD_ACTIVE_POWER: values[1] if len(values) > 1 else 0,  # Reg 4409 (index 1) in W
                KEY_INVERTER_LOAD_APPARENT_POWER: values[2] if len(values) > 2 else 0,  # Reg 4410 (index 2) in VA
            }

            return parsed

        except Exception as e:
            self.logger.error("Error parsing load response: %s", e, exc_info=True)
            return {}

    def _parse_device_id_response(self, data: bytes) -> dict[str, Any]:
        """Parse Modbus response from register 4109 (Device ID)."""
        from .sensor import KEY_INVERTER_DEVICE_ID

        try:
            if len(data) < 5:
                return {}

            # Extract single register value (big-endian 16-bit word)
            if len(data) >= 5:
                device_id = struct.unpack('>H', data[3:5])[0]
                return {KEY_INVERTER_DEVICE_ID: device_id}

            return {}

        except Exception as e:
            self.logger.error("Error parsing device ID response: %s", e, exc_info=True)
            return {}

    def _parse_model_response(self, data: bytes) -> dict[str, Any]:
        """Parse Modbus response from register 4311 (Model String)."""
        from .sensor import KEY_INVERTER_MODEL

        try:
            if len(data) < 5:
                return {}

            # Extract 8 registers (16 bytes) as ASCII string
            # Data starts at byte 3, model is 16 bytes
            if len(data) >= 19:
                model_bytes = data[3:19]
                # Decode as ASCII and strip null bytes
                model_str = model_bytes.decode('ascii', errors='ignore').rstrip('\x00')
                return {KEY_INVERTER_MODEL: model_str}

            return {}

        except Exception as e:
            self.logger.error("Error parsing model response: %s", e, exc_info=True)
            return {}

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
