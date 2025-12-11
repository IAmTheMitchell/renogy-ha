"""BLE communication module for Renogy devices."""

import asyncio
import logging
import re
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
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

from .const import (
    COMMANDS,
    DEFAULT_DEVICE_ID,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    LOGGER,
    MAX_NOTIFICATION_WAIT_TIME,
    RENOGY_READ_CHAR_UUID,
    RENOGY_WRITE_CHAR_UUID,
    UNAVAILABLE_RETRY_INTERVAL,
)

try:
    from renogy_ble import RenogyParser

    PARSER_AVAILABLE = True
except ImportError:
    LOGGER.error("renogy-ble library not found! Please re-install the integration")
    RenogyParser = None
    PARSER_AVAILABLE = False


def modbus_crc(data: bytes) -> tuple:
    """Calculate the Modbus CRC16 of the given data.

    Returns a tuple (crc_low, crc_high) where the low byte is sent first.
    """
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return (crc & 0xFF, (crc >> 8) & 0xFF)


def create_modbus_read_request(
    device_id: int, function_code: int, register: int, word_count: int
) -> bytearray:
    """Build a Modbus read request frame.

    The frame consists of:
      [device_id, function_code, register_high, register_low, word_count_high,
      word_count_low, crc_high, crc_low]

    Note: Many Modbus implementations send the CRC as low byte first; adjust if needed.
    """
    frame = bytearray(
        [
            device_id,
            function_code,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (word_count >> 8) & 0xFF,
            word_count & 0xFF,
        ]
    )
    crc_low, crc_high = modbus_crc(frame)
    frame.extend([crc_low, crc_high])
    LOGGER.debug("create_request_payload: %s (%s)", register, list(frame))
    return frame


def clean_device_name(name: str) -> str:
    """Clean the device name by removing unwanted characters."""

    if name:
        cleaned_name = name.strip()
        cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip()
        return cleaned_name
    else:
        return ""


class RenogyBLEDevice:
    """Representation of a Renogy BLE device."""

    def __init__(
        self,
        ble_device: BLEDevice,
        advertisement_rssi: Optional[int] = None,
        device_type: str = DEFAULT_DEVICE_TYPE,
    ):
        """Initialize the Renogy BLE device."""
        self.ble_device = ble_device
        self.address = ble_device.address

        cleaned_name = clean_device_name(ble_device.name)
        self.name = cleaned_name or "Unknown Renogy Device"

        # Use the provided advertisement RSSI if available, otherwise set to None
        self.rssi = advertisement_rssi
        self.last_seen = datetime.now()
        # To store last received data
        self.data: Optional[Dict[str, Any]] = None
        # Track consecutive failures
        self.failure_count = 0
        # Maximum allowed failures before marking device unavailable
        self.max_failures = 3
        # Device availability tracking
        self.available = True
        # Parsed data from device
        self.parsed_data: Dict[str, Any] = {}
        # Device type - set from configuration
        self.device_type = device_type
        # Track when device was last marked as unavailable
        self.last_unavailable_time: Optional[datetime] = None

    @property
    def is_available(self) -> bool:
        """Return True if device is available."""
        return self.available and self.failure_count < self.max_failures

    @property
    def should_retry_connection(self) -> bool:
        """Check if we should retry connecting to an unavailable device."""
        if self.is_available:
            return True

        # If we've never set an unavailable time, set it now
        if self.last_unavailable_time is None:
            self.last_unavailable_time = datetime.now()
            return False

        # Check if enough time has elapsed since the last poll
        retry_time = self.last_unavailable_time + timedelta(
            minutes=UNAVAILABLE_RETRY_INTERVAL
        )
        if datetime.now() >= retry_time:
            LOGGER.debug(
                "Retry interval reached for unavailable device %s. "
                "Attempting reconnection...",
                self.name,
            )
            # Reset the unavailable time for the next retry interval
            self.last_unavailable_time = datetime.now()
            return True

        return False

    def update_availability(
        self, success: bool, error: Optional[Exception] = None
    ) -> None:
        """Update the availability based on success/failure of communication."""
        if success:
            if self.failure_count > 0:
                LOGGER.info(
                    "Device %s communication restored after %s consecutive failures",
                    self.name,
                    self.failure_count,
                )
            self.failure_count = 0
            if not self.available:
                LOGGER.info("Device %s is now available", self.name)
                self.available = True
                self.last_unavailable_time = None
        else:
            self.failure_count += 1
            error_msg = f" Error message: {str(error)}" if error else ""
            LOGGER.info(
                "Communication failure with Renogy device: %s. "
                "(Consecutive polling failure #%s. "
                "Device will be marked unavailable after %s failures.)%s",
                self.name,
                self.failure_count,
                self.max_failures,
                error_msg,
            )

            if self.failure_count >= self.max_failures and self.available:
                error_msg = f". Error message: {str(error)}" if error else ""
                LOGGER.error(
                    "Renogy device %s marked unavailable after %s "
                    "consecutive polling failures%s",
                    self.name,
                    self.max_failures,
                    error_msg,
                )
                self.available = False
                self.last_unavailable_time = datetime.now()
                
    def _correct_temperature_offset(self, parsed_data: Dict[str, Any]) -> None:
        """Correct temperature values that have an offset encoding.
        
        Some Renogy devices send temperature with a 130-degree offset:
        - 130 = 0°C
        - 129 = -1°C  
        - 131 = 1°C
        
        This method detects and corrects these offset values.
        """
        temp_keys = ["battery_temperature", "controller_temperature"]
        
        for key in temp_keys:
            if key in parsed_data:
                temp = parsed_data[key]
                
                # Check if this looks like an offset-encoded temperature
                # Valid range is -40 to 85°C, so anything above 85 is likely offset-encoded
                if isinstance(temp, (int, float)) and temp > 85:
                    corrected_temp = temp - 130
                    
                    # Verify the corrected value is within valid range
                    if -40 <= corrected_temp <= 85:
                        LOGGER.debug(
                            "%s %s: Corrected temperature from %.1f to %.1f°C (offset encoding detected)",
                            self.name,
                            key.replace('_', ' ').title(),
                            temp,
                            corrected_temp
                        )
                        parsed_data[key] = corrected_temp
                    else:
                        LOGGER.warning(
                            "%s %s: Temperature %.1f°C appears invalid even after offset correction (%.1f°C)",
                            self.name,
                            key.replace('_', ' ').title(),
                            temp,
                            corrected_temp
                        )

    def update_parsed_data(
        self, raw_data: bytes, register: int, cmd_name: str = "unknown"
    ) -> bool:
        """Parse the raw data using the renogy-ble library.

        Args:
            raw_data: The raw data received from the device
            register: The register address this data corresponds to
            cmd_name: The name of the command (for logging purposes)

        Returns:
            True if parsing was successful (even partially), False otherwise
        """
        if not raw_data:
            LOGGER.error(
                "Attempted to parse empty data from device %s for command %s.",
                self.name,
                cmd_name,
            )
            return False

        if not PARSER_AVAILABLE:
            LOGGER.error("RenogyParser library not available. Unable to parse data.")
            return False

        try:
            # Check for minimum valid response length
            # Modbus response format: device_id(1) + function_code(1) +
            # byte_count(1) + data(n) + crc(2).
            if (
                len(raw_data) < 5
            ):  # At minimum, we need these 5 bytes for a valid response
                LOGGER.warning(
                    "Response too short for %s: %s bytes. Raw data: %s",
                    cmd_name,
                    len(raw_data),
                    raw_data.hex(),
                )
                return False

            # Basic validation of Modbus response
            # Ensure the complete Modbus frame is present:
            # 3‑byte header + data + 2‑byte CRC.
            byte_count = raw_data[2]
            expected_len = 3 + byte_count + 2
            if len(raw_data) < expected_len:
                LOGGER.warning(
                    "Got only %s / %s bytes for %s (register %s). Raw: %s",
                    len(raw_data),
                    expected_len,
                    cmd_name,
                    register,
                    raw_data.hex(),
                )
                return False
            function_code = raw_data[1] if len(raw_data) > 1 else 0
            if function_code & 0x80:  # Error response
                error_code = raw_data[2] if len(raw_data) > 2 else 0
                LOGGER.error(
                    "Modbus error in %s response: function code %s, error code %s",
                    cmd_name,
                    function_code,
                    error_code,
                )
                return False

            # Parse the raw data using the renogy-ble library
            # The parser will handle partial data and log appropriate warnings
            parsed = RenogyParser.parse(raw_data, self.device_type, register)

            if not parsed:
                LOGGER.warning(
                    "No data parsed from %s response (register %s). Length: %s",
                    cmd_name,
                    register,
                    len(raw_data),
                )
                return False

            # Update the stored parsed data with whatever we could get
            # Apply temperature correction for devices that use offset encoding
            self._correct_temperature_offset(parsed)
            self.parsed_data.update(parsed)

            # Log the successful parsing
            LOGGER.debug(
                "Successfully parsed %s data from device %s: %s",
                cmd_name,
                self.name,
                parsed,
            )
            return True

        except Exception as e:
            LOGGER.error(
                "Error parsing %s data from device %s: %s", cmd_name, self.name, str(e)
            )
            # Log additional debug info to help diagnose the issue
            LOGGER.debug(
                "Raw data for %s (register %s): %s, Length: %s",
                cmd_name,
                register,
                raw_data.hex() if raw_data else "None",
                len(raw_data) if raw_data else 0,
            )
            return False


class RenogyActiveBluetoothCoordinator(ActiveBluetoothDataUpdateCoordinator):
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
            poll_method=self._async_poll,
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

        # Add required properties for Home Assistant CoordinatorEntity compatibility
        self.last_update_success = True
        self._listeners = []
        self.update_interval = timedelta(seconds=scan_interval)
        self._unsub_refresh = None
        self._request_refresh_task = None

        # Add connection lock to prevent multiple concurrent connections
        self._connection_lock = asyncio.Lock()
        self._connection_in_progress = False

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
            await self._async_poll(service_info)
            self.last_update_success = True
            # Notify listeners of the update
            for update_callback in self._listeners:
                update_callback()
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
        if update_callback not in self._listeners:
            self._listeners.append(update_callback)

        def remove_listener() -> None:
            """Remove update callback."""
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return remove_listener

    def async_update_listeners(self) -> None:
        """Update all registered listeners."""
        for update_callback in self._listeners:
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
        self._listeners = []

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
        async with self._connection_lock:
            try:
                self._connection_in_progress = True
                success = False
                error = None

                # Use service_info to get a BLE device and update our device object
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
                    # Store the old name to detect changes
                    old_name = self.device.name

                    self.device.ble_device = service_info.device
                    # Update name if available from service_info
                    if (
                        service_info.name
                        and service_info.name != "Unknown Renogy Device"
                    ):
                        cleaned_name = clean_device_name(service_info.name)
                        if old_name != cleaned_name:
                            self.device.name = cleaned_name
                            self.logger.debug(
                                "Updated device name from '%s' to '%s'",
                                old_name,
                                cleaned_name,
                            )

                    # Prefer the RSSI from advertisement data if available
                    self.device.rssi = (
                        service_info.advertisement.rssi
                        if service_info.advertisement
                        and service_info.advertisement.rssi is not None
                        else service_info.device.rssi
                    )

                    # Ensure device type is set correctly
                    if self.device.device_type != self.device_type:
                        self.logger.debug(
                            "Updating device type from '%s' to '%s'",
                            self.device.device_type,
                            self.device_type,
                        )
                        self.device.device_type = self.device_type

                device = self.device
                self.logger.debug(
                    "Polling %s device: %s (%s)",
                    device.device_type,
                    device.name,
                    device.address,
                )

                # Use bleak-retry-connector for more robust connection
                try:
                    # Establish connection with retry capability
                    client = await establish_connection(
                        BleakClientWithServiceCache,
                        service_info.device,
                        device.name or device.address,
                        max_attempts=3,
                    )

                    any_command_succeeded = False

                    try:
                        self.logger.debug("Connected to device %s", device.name)

                        # Create an event for when notification data is received.
                        notification_event = asyncio.Event()
                        notification_data = bytearray()

                        def notification_handler(sender, data):
                            notification_data.extend(data)
                            notification_event.set()

                        await client.start_notify(
                            RENOGY_READ_CHAR_UUID, notification_handler
                        )

                        for cmd_name, cmd in COMMANDS[self.device_type].items():
                            notification_data.clear()
                            notification_event.clear()

                            modbus_request = create_modbus_read_request(
                                DEFAULT_DEVICE_ID, *cmd
                            )
                            self.logger.debug(
                                "Sending %s command: %s",
                                cmd_name,
                                list(modbus_request),
                            )
                            await client.write_gatt_char(
                                RENOGY_WRITE_CHAR_UUID, modbus_request
                            )

                            # Expected length: 3 header bytes +
                            # 2*word_count data + 2‑byte CRC.
                            word_count = cmd[2]
                            expected_len = 3 + word_count * 2 + 2
                            start_time = self.hass.loop.time()

                            try:
                                while len(notification_data) < expected_len:
                                    remaining = MAX_NOTIFICATION_WAIT_TIME - (
                                        self.hass.loop.time() - start_time
                                    )
                                    if remaining <= 0:
                                        raise asyncio.TimeoutError()
                                    await asyncio.wait_for(
                                        notification_event.wait(), remaining
                                    )
                                    notification_event.clear()
                            except asyncio.TimeoutError:
                                self.logger.info(
                                    "Timeout – only %s / %s bytes received for %s "
                                    "from device %s",
                                    len(notification_data),
                                    expected_len,
                                    cmd_name,
                                    device.name,
                                )
                                continue

                            result_data = bytes(notification_data[:expected_len])
                            self.logger.debug(
                                "Received %s data length: %s (expected %s)",
                                cmd_name,
                                len(result_data),
                                expected_len,
                            )

                            cmd_success = device.update_parsed_data(
                                result_data, register=cmd[1], cmd_name=cmd_name
                            )

                            if cmd_success:
                                self.logger.debug(
                                    "Successfully read and parsed %s data from "
                                    "device %s",
                                    cmd_name,
                                    device.name,
                                )
                                any_command_succeeded = True
                            else:
                                self.logger.info(
                                    "Failed to parse %s data from device %s",
                                    cmd_name,
                                    device.name,
                                )

                        await client.stop_notify(RENOGY_READ_CHAR_UUID)
                        success = any_command_succeeded
                        if not success:
                            error = Exception("No commands completed successfully")

                    except BleakError as e:
                        self.logger.info(
                            "BLE error with device %s: %s", device.name, str(e)
                        )
                        error = e
                        success = False
                    except Exception as e:
                        self.logger.error(
                            "Error reading data from device %s: %s", device.name, str(e)
                        )
                        error = e
                        success = False
                    finally:
                        # BleakClientWithServiceCache handles disconnect in context
                        # manager.
                        # But we need to ensure the client is disconnected.
                        if client.is_connected:
                            try:
                                await client.disconnect()
                                self.logger.debug(
                                    "Disconnected from device %s", device.name
                                )
                            except Exception as e:
                                self.logger.debug(
                                    "Error disconnecting from device %s: %s",
                                    device.name,
                                    str(e),
                                )
                                # Don't override previous errors with disconnect errors
                                if error is None:
                                    error = e

                except (BleakError, asyncio.TimeoutError) as connection_error:
                    self.logger.info(
                        "Failed to establish connection with device %s: %s",
                        device.name,
                        str(connection_error),
                    )
                    error = connection_error
                    success = False

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

    async def _async_poll(self, service_info: BluetoothServiceInfoBleak) -> None:
        """Poll the device."""
        # If a connection is already in progress, don't start another one
        if self._connection_in_progress:
            self.logger.debug("Connection already in progress, skipping poll")
            return

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
            self.async_update_listeners()

        else:
            self.logger.info("Failed to retrieve data from %s", service_info.address)
            self.last_update_success = False

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
