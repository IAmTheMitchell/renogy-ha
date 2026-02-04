"""BLE communication module for Renogy devices."""

import asyncio
import importlib
import logging
import traceback
from datetime import datetime, timedelta
from types import ModuleType
from typing import Any, Awaitable, Callable, Optional, cast

from bleak import BleakError
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

from .const import DEFAULT_DEVICE_TYPE, DEFAULT_SCAN_INTERVAL, DeviceType
from .shunt_handler import ShuntNotificationHandler

LOAD_CONTROL_REGISTER = getattr(renogy_ble_module, "LOAD_CONTROL_REGISTER", 0x010A)


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

        self._ble_client = RenogyBleClient(scanner=bluetooth.async_get_scanner(hass))

        # Add required properties for Home Assistant CoordinatorEntity compatibility
        self.last_update_success = True
        self._update_listeners: list[Callable[[], None]] = []
        self.update_interval = (
            None
            if device_type == DeviceType.SHUNT.value
            else timedelta(seconds=scan_interval)
        )
        self._unsub_refresh = None
        self._request_refresh_task = None

        # Add connection lock to prevent multiple concurrent connections
        self._connection_lock = asyncio.Lock()
        self._connection_in_progress = False

        # SHUNT-specific handler for continuous notifications
        self.shunt_handler: Optional[ShuntNotificationHandler] = None
        self._shunt_connection_attempted = False
        self._shunt_last_attempt: Optional[datetime] = None

    @property
    def device_type(self) -> str:
        """Get the device type from configuration."""
        return self._device_type

    @device_type.setter
    def device_type(self, value: str) -> None:
        """Set the device type."""
        self._device_type = value
        if hasattr(self, "scan_interval"):
            if value == DeviceType.SHUNT.value:
                self.update_interval = None
            else:
                self.update_interval = timedelta(seconds=self.scan_interval)

    async def async_request_refresh(self) -> None:
        """Request a refresh."""
        self.logger.debug("Manual refresh requested for device %s", self.address)

        # For SHUNT - allow connection attempts with backoff to avoid BLE slot contention
        if self.device_type == DeviceType.SHUNT.value:
            if self.shunt_handler and self.shunt_handler.is_connected:
                self.logger.debug(
                    "SHUNT already connected via notifications, skipping refresh"
                )
                return

            now = datetime.now()
            if self._shunt_last_attempt and now - self._shunt_last_attempt < timedelta(
                minutes=5
            ):
                self.logger.debug(
                    "SHUNT backoff active, skipping refresh to avoid BLE slot contention"
                )
                return

            self.logger.debug("SHUNT connection attempt allowed, proceeding...")

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
        interval_seconds = (
            int(self.update_interval.total_seconds())
            if self.update_interval
            else "none"
        )
        self.logger.debug("Scheduled next refresh in %s seconds", interval_seconds)

    async def _handle_refresh_interval(self, _now=None):
        """Handle a refresh interval occurring."""
        self.logger.debug("Regular interval refresh for %s", self.address)

        # For SHUNT, only retry when not connected; backoff handled in async_request_refresh
        if self.device_type == DeviceType.SHUNT.value:
            if self.shunt_handler and self.shunt_handler.is_connected:
                self.logger.debug("SHUNT already connected, skipping interval refresh")
                return
            await self.async_request_refresh()
            return

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

        # SHUNT devices use notification-based updates, not polling intervals
        if self.device_type != DeviceType.SHUNT.value:
            # Schedule regular refreshes at our configured interval for non-SHUNT devices
            self._schedule_refresh()
            # Perform an initial refresh to get data as soon as possible
            self.hass.async_create_task(self.async_request_refresh())
        else:
            # For SHUNT, schedule a slow retry interval to avoid BLE slot contention
            # Connection happens via notifications; retries are spaced out
            self._shunt_connection_attempted = False
            self.update_interval = timedelta(minutes=5)
            self._schedule_refresh()
            self.logger.debug(
                "SHUNT device: notifications with 5-minute retry backoff"
            )

        return result

    def _async_cancel_bluetooth_subscription(self) -> None:
        """Cancel the bluetooth subscription."""
        if hasattr(self, "_unsubscribe_bluetooth") and self._unsubscribe_bluetooth:
            self._unsubscribe_bluetooth()
            self._unsubscribe_bluetooth = None

    def async_stop(self) -> None:
        """Stop polling."""
        # Cleanup SHUNT handler if present
        if self.shunt_handler and self.shunt_handler.is_connected:
            try:
                # Create async task for disconnection if event loop is running
                if self.hass.is_running:
                    self.hass.async_create_task(self.shunt_handler.disconnect())
                else:
                    # Fallback for sync context
                    import asyncio
                    try:
                        asyncio.run(self.shunt_handler.disconnect())
                    except:
                        pass
            except Exception as e:
                self.logger.debug(f"Error disconnecting SHUNT handler: {e}")
            self.shunt_handler = None
        
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
        if not self.device:
            self.logger.debug(
                "Creating new RenogyBLEDevice for %s as %s",
                service_info.address,
                self.device_type,
            )
            self.device = RenogyBLEDevice(
                service_info.device,
                service_info.advertisement.rssi,
                device_type=self.device_type,
            )
        else:
            old_name = self.device.name
            self.device.ble_device = service_info.device
            if service_info.name and service_info.name != "Unknown Renogy Device":
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

        # SHUNT devices use notification-based updates, not regular polling
        # Allow connection attempts with backoff, then skip to avoid contention
        if self.device_type == DeviceType.SHUNT.value:
            if self.shunt_handler and self.shunt_handler.is_connected:
                self.logger.debug(
                    "SHUNT already connected via notifications, skipping poll cycle"
                )
                return False

            now = datetime.now()
            if self._shunt_last_attempt is None:
                self.logger.debug("SHUNT first connection - allowing poll for setup")
                return True
            if now - self._shunt_last_attempt >= timedelta(minutes=5):
                self.logger.debug("SHUNT backoff elapsed - allowing retry poll")
                return True

            self.logger.debug("SHUNT backoff active, skipping poll cycle")
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

                # Check if this is a SHUNT device (uses notifications instead of polling)
                if device.device_type == DeviceType.SHUNT.value:
                    # If SHUNT handler is already connected and streaming, skip reconnection
                    if self.shunt_handler and self.shunt_handler.is_connected:
                        self.logger.debug("SHUNT already connected and streaming, skipping poll")
                        # Update availability to True since notifications are active
                        device.update_availability(True, None)
                        self.last_update_success = True
                        return True
                    # Otherwise, setup/reconnect the handler
                    success = await self._setup_shunt_handler(device, service_info)
                else:
                    # Standard Modbus polling for controllers, batteries, etc.
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
                    self.data = dict(device.parsed_data)
                    self.logger.debug("Updated coordinator data: %s", self.data)

                return success
            finally:
                self._connection_in_progress = False

    async def _setup_shunt_handler(
        self, device: RenogyBLEDevice, service_info: BluetoothServiceInfoBleak
    ) -> bool:
        """Setup and manage SHUNT notification handler.
        
        Args:
            device: Renogy device instance
            service_info: BLE service info
        
        Returns:
            True if handler is active, False otherwise
        """
        # Mark that we've attempted SHUNT connection
        self._shunt_connection_attempted = True
        self._shunt_last_attempt = datetime.now()
        
        try:
            # Create handler if needed
            if self.shunt_handler is None:
                self.shunt_handler = ShuntNotificationHandler(
                    self.hass,
                    device.address,
                    self._process_shunt_data,
                    self.logger,
                )
                self.logger.info(f"Created SHUNT handler for {device.address}")
            
            # Connect if not already connected
            if not self.shunt_handler.is_connected:
                success = await self.shunt_handler.connect_and_listen()
                if not success:
                    self.logger.error(f"Failed to connect SHUNT handler for {device.address}")
                    # Mark failure to prevent retries during polling windows
                    self._shunt_connection_attempted = True
                    return False
                self.logger.info(f"SHUNT handler connected for {device.address}")
            
            # Update device status
            device.update_availability(True, None)
            self.last_update_success = True
            
            return True
        
        except Exception as err:
            self.logger.error(f"SHUNT handler error: {err}", exc_info=True)
            device.update_availability(False, err)
            return False

    def _process_shunt_data(self, parsed_data: dict[str, Any]) -> None:
        """Process parsed SHUNT telemetry data from notification handler.
        
        Args:
            parsed_data: Pre-parsed SHUNT packet data (dict with sensor values)
        """
        try:
            if not parsed_data:
                return
            
            # Data is already parsed by the handler, just update coordinator
            self.data = parsed_data
            self.last_update_success = True
            
            # Update device if it exists
            if self.device:
                self.device.parsed_data = parsed_data
                self.device.update_availability(True, None)
            
            # Notify all listeners of data update
            self.async_update_listeners()
            
            self.logger.debug(
                f"SHUNT data updated: V={parsed_data.get('battery_voltage'):.2f}V "
                f"I={parsed_data.get('battery_current'):.2f}A "
                f"SOC={parsed_data.get('state_of_charge'):.1f}%"
            )
        
        except Exception as err:
            self.logger.error(f"Error processing SHUNT data: {err}", exc_info=True)


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
