"""Renogy Smart SHUNT BLE notification handler.

This module handles continuous telemetry streams from Renogy Smart SHUNT devices,
which send autonomous BLE notifications (unlike other Renogy devices which use polling).
"""

import asyncio
import logging
from typing import Callable, Optional, Any

from bleak import BleakClient, BleakError
from homeassistant.core import HomeAssistant

from .shunt_parser import parse_shunt_packet, SHUNT_RX_UUID, SHUNT_SERVICE_UUID

LOGGER = logging.getLogger(__name__)


class ShuntNotificationHandler:
    """Handle continuous notifications from Renogy Smart SHUNT."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_address: str,
        data_callback: Callable[[dict], None],
        logger: logging.Logger,
    ):
        """Initialize SHUNT notification handler.
        
        Args:
            hass: Home Assistant instance
            device_address: BLE MAC address of SHUNT device
            data_callback: Callback function to call with parsed data
            logger: Logger instance
        """
        self.hass = hass
        self.device_address = device_address
        self.data_callback = data_callback
        self.logger = logger
        
        self.client: Optional[BleakClient] = None
        self._notification_enabled = False
        self._last_sequence = -1
        self._packet_count = 0
        self._parse_errors = 0

    async def connect_and_listen(self) -> bool:
        """Connect to SHUNT and start listening for notifications.
        
        Returns:
            True if successfully connected and listening, False otherwise
        """
        try:
            self.logger.debug(f"Connecting to SHUNT at {self.device_address}")
            
            # Use BleakClient with auto-reconnect
            self.client = BleakClient(self.device_address)
            
            # Connect with timeout
            await asyncio.wait_for(self.client.connect(), timeout=10.0)
            
            if not self.client.is_connected:
                self.logger.error(f"Failed to connect to {self.device_address}")
                return False
            
            self.logger.info(f"Connected to SHUNT at {self.device_address}")
            
            # Start listening for notifications
            try:
                await self.client.start_notify(SHUNT_RX_UUID, self._notification_handler)
                self._notification_enabled = True
                self.logger.info(f"Listening for SHUNT notifications on {SHUNT_RX_UUID}")
                return True
            except BleakError as err:
                self.logger.error(f"Failed to enable notifications: {err}")
                await self.client.disconnect()
                return False
        
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout connecting to {self.device_address}")
            return False
        except Exception as err:
            self.logger.error(f"Connection error: {err}")
            return False

    def _notification_handler(self, sender, data: bytes) -> None:
        """Handle incoming BLE notification.
        
        Args:
            sender: BLE characteristic that sent notification
            data: Raw notification data
        """
        try:
            # Parse packet
            parsed = parse_shunt_packet(data)
            
            if parsed is None:
                self._parse_errors += 1
                if self._parse_errors > 10:
                    self.logger.warning(
                        f"Multiple parse errors ({self._parse_errors}), may indicate connection issue"
                    )
                return
            
            # Track packet sequencing
            current_seq = parsed.get("sequence", -1)
            try:
                current_seq = int(current_seq)
            except (TypeError, ValueError):
                current_seq = -1

            if self._last_sequence >= 0 and current_seq >= 0:
                # Check for sequence jump (not exactly +1)
                expected_seq = (self._last_sequence + 1) & 0xFFFF
                if current_seq != expected_seq:
                    self.logger.debug(
                        f"Sequence jump: expected {expected_seq}, got {current_seq} "
                        "(may indicate packet loss)"
                    )
            
            self._last_sequence = current_seq
            self._packet_count += 1
            
            # Reset parse error counter on successful parse
            if self._parse_errors > 0:
                self._parse_errors = 0
            
            # Call callback with parsed data
            self.data_callback(parsed)
            
            # Log at debug level to avoid spam (8.5 packets/sec)
            if self._packet_count % 100 == 0:
                self.logger.debug(
                    f"Processed {self._packet_count} SHUNT packets, last V={parsed.get('battery_voltage')}V"
                )
        
        except Exception as err:
            self.logger.error(f"Error in notification handler: {err}", exc_info=True)

    async def disconnect(self) -> None:
        """Disconnect from SHUNT and stop listening."""
        try:
            if self.client:
                if self._notification_enabled:
                    try:
                        await self.client.stop_notify(SHUNT_RX_UUID)
                    except Exception as err:
                        self.logger.debug(f"Error stopping notifications: {err}")
                
                await self.client.disconnect()
                self._notification_enabled = False
                self.logger.info(f"Disconnected from SHUNT at {self.device_address}")
        except Exception as err:
            self.logger.error(f"Error during disconnect: {err}")

    @property
    def is_connected(self) -> bool:
        """Check if SHUNT is connected."""
        return self.client is not None and self.client.is_connected

    @property
    def packet_count(self) -> int:
        """Get number of processed packets."""
        return self._packet_count
