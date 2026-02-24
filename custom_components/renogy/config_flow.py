"""Config flow for Renogy BLE integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_SCAN_INTERVAL

from .const import (
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPES,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUPPORTED_DEVICE_TYPES,
)
from .device_name import detect_device_type_from_ble_name, is_supported_renogy_ble_name

# Common schema fields for device configuration
DEVICE_TYPE_SCHEMA = {
    vol.Required(CONF_DEVICE_TYPE, default=DEFAULT_DEVICE_TYPE): vol.In(DEVICE_TYPES),
}

SCAN_INTERVAL_SCHEMA = {
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
        vol.Coerce(int),
        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
    ),
}

# Base configuration schema without device selection
CONFIG_SCHEMA = vol.Schema({**DEVICE_TYPE_SCHEMA, **SCAN_INTERVAL_SCHEMA})


class RenogyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Renogy BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._discovered_device: BluetoothServiceInfoBleak | None = None
        self._default_device_type: str = DEFAULT_DEVICE_TYPE

    def _is_renogy_device(self, discovery_info: BluetoothServiceInfoBleak) -> bool:
        """Check if a BLE device advertises a supported Renogy name."""
        return is_supported_renogy_ble_name(discovery_info.name)

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        # Check if this is a Renogy device based on the name
        if not self._is_renogy_device(discovery_info):
            return self.async_abort(reason="not_supported_device")

        LOGGER.debug(
            "Bluetooth auto-discovery for Renogy device: %s (%s)",
            discovery_info.name,
            discovery_info.address,
        )

        # Set unique ID and check if already configured
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Store the discovered device for later
        self._discovered_device = discovery_info
        self._default_device_type = detect_device_type_from_ble_name(
            discovery_info.name, DEFAULT_DEVICE_TYPE
        )

        # Set title to user-readable name
        self.context["title_placeholders"] = {
            "name": discovery_info.name,
            "address": discovery_info.address,
        }

        # Proceed to configuration options
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick discovered device or configure options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if the selected device type is supported
            if (
                CONF_DEVICE_TYPE in user_input
                and user_input[CONF_DEVICE_TYPE] not in SUPPORTED_DEVICE_TYPES
            ):
                device_type = user_input[CONF_DEVICE_TYPE]
                LOGGER.warning("Unsupported device type selected: %s", device_type)

                # Generate a user-friendly error message with the device type
                return self.async_abort(
                    reason="unsupported_device_type",
                    description_placeholders={"device_type": device_type},
                )

            if self._discovered_device:
                # Coming from bluetooth discovery with device already selected
                user_input[CONF_ADDRESS] = self._discovered_device.address

                # Create a config entry
                return self.async_create_entry(
                    title=self._discovered_device.name,
                    data=user_input,
                )
            elif CONF_ADDRESS in user_input:
                # Manual device selection
                address = user_input[CONF_ADDRESS]
                discovery_info = self._discovered_devices[address]

                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=discovery_info.name,
                    data=user_input,
                )

        # If we have a discovered device from bluetooth auto-discovery,
        # just show config options (scan interval, etc)
        if self._discovered_device:
            discovered_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_TYPE, default=self._default_device_type
                    ): vol.In(DEVICE_TYPES),
                    **SCAN_INTERVAL_SCHEMA,
                }
            )
            return self.async_show_form(
                step_id="user",
                data_schema=discovered_schema,
                description_placeholders={
                    "device_name": self._discovered_device.name,
                    "default_interval": str(DEFAULT_SCAN_INTERVAL),
                },
                errors=errors,
            )

        # Otherwise, scan for available devices to let the user pick one
        await self._async_discover_devices()

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # Show form to select a discovered device
        address_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        address: f"{info.name} ({address})"
                        for address, info in self._discovered_devices.items()
                    }
                ),
                **DEVICE_TYPE_SCHEMA,
                **SCAN_INTERVAL_SCHEMA,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=address_schema,
            description_placeholders={
                "device_name": "Select below",
                "default_interval": str(DEFAULT_SCAN_INTERVAL),
            },
            errors=errors,
        )

    async def _async_discover_devices(self) -> None:
        """Discover Bluetooth devices."""
        LOGGER.debug("Scanning for Renogy BLE devices")

        self._discovered_devices = {}

        for discovery_info in bluetooth.async_discovered_service_info(self.hass):
            # Skip devices that don't match our pattern
            if not self._is_renogy_device(discovery_info):
                continue

            # Skip devices that are already configured
            address = discovery_info.address
            if address in self._async_current_ids():
                continue

            # Add to list of discovered devices
            self._discovered_devices[address] = discovery_info
            LOGGER.debug("Found Renogy device: %s (%s)", discovery_info.name, address)

        LOGGER.debug(
            "Found %s unconfigured Renogy devices", len(self._discovered_devices)
        )
