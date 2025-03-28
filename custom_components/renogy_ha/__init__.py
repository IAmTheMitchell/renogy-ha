"""Renogy BLE integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

# List of platforms this integration supports
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renogy BLE from a config entry."""
    LOGGER.info(f"Setting up Renogy BLE integration with entry {entry.entry_id}")

    # Get configuration from entry
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    device_address = entry.data.get(CONF_ADDRESS)

    if not device_address:
        LOGGER.error("No device address provided in config entry")
        return False

    LOGGER.info(
        f"Configuring Renogy BLE device {device_address} with scan interval {scan_interval}s"
    )

    # Create a coordinator for this entry
    coordinator = RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=LOGGER,
        address=device_address,
        scan_interval=scan_interval,
        device_data_callback=lambda device: hass.async_create_task(
            _handle_device_update(hass, entry, device)
        ),
    )

    # Store coordinator and devices in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "devices": [],  # Will be populated as devices are discovered
        "initialized_devices": set(),  # Track which devices have entities
    }

    # Forward entry setup to sensor platform
    LOGGER.info(f"Setting up sensor platform for Renogy BLE device {device_address}")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start the coordinator after all platforms are set up
    # This ensures all entities have had a chance to subscribe to the coordinator
    LOGGER.info(f"Starting coordinator for Renogy BLE device {device_address}")
    entry.async_on_unload(coordinator.async_start())

    # Force an immediate refresh
    LOGGER.info(f"Requesting initial refresh for Renogy BLE device {device_address}")
    hass.async_create_task(coordinator.async_request_refresh())

    return True


async def _handle_device_update(
    hass: HomeAssistant, entry: ConfigEntry, device: RenogyBLEDevice
) -> None:
    """Handle device update callback."""
    LOGGER.info(f"Device update for {device.name} ({device.address})")

    # Make sure the device is in our registry
    if entry.entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry.entry_id]
        devices_list = entry_data.get("devices", [])

        # Check if device is already in list by address
        device_addresses = [d.address for d in devices_list]
        if device.address not in device_addresses:
            LOGGER.info(f"Adding device {device.name} to registry")
            devices_list.append(device)

            # Log the parsed data for debugging
            if device.parsed_data:
                LOGGER.debug(f"Device data: {device.parsed_data}")
            else:
                LOGGER.warning(f"No parsed data for device {device.name}")

        # Update the device name in the Home Assistant device registry
        # This will ensure the device name is updated in the UI
        if device.name != "Unknown Renogy Device" and not device.name.startswith(
            "Unknown"
        ):
            hass.async_create_task(update_device_registry(hass, entry, device))


async def update_device_registry(
    hass: HomeAssistant, entry: ConfigEntry, device: RenogyBLEDevice
) -> None:
    """Update device in registry."""
    try:
        from .const import ATTR_MANUFACTURER, ATTR_MODEL

        device_registry = async_get_device_registry(hass)
        model = (
            device.parsed_data.get("model", ATTR_MODEL)
            if device.parsed_data
            else ATTR_MODEL
        )

        # Find the device in the registry using the domain and device address
        device_entry = device_registry.async_get_device({(DOMAIN, device.address)})

        if device_entry:
            # Update the device name
            LOGGER.info(f"Updating device registry entry with real name: {device.name}")
            device_registry.async_update_device(
                device_entry.id, name=device.name, model=model
            )
        else:
            LOGGER.warning(f"Device {device.address} not found in registry for update")
    except Exception as e:
        LOGGER.error(f"Error updating device in registry: {e}")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.info(f"Unloading Renogy BLE integration for {entry.entry_id}")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.entry_id in hass.data[DOMAIN]:
        # Stop the coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        coordinator.async_stop()

        # Remove entry from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
