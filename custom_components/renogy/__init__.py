"""Renogy BLE integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    CONF_DEVICE_TYPE,
    CONF_SCAN_INTERVAL,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)

# List of platforms this integration supports
PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renogy BLE from a config entry."""
    LOGGER.info("Setting up Renogy BLE integration with entry %s", entry.entry_id)

    # Get configuration from entry
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    device_address = entry.data.get(CONF_ADDRESS)
    device_type = entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)

    if not device_address:
        LOGGER.error("No device address provided in config entry")
        return False

    LOGGER.info(
        "Configuring Renogy BLE device %s as %s with scan interval %ss",
        device_address,
        device_type,
        scan_interval,
    )

    # Create a coordinator for this entry
    coordinator = RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=LOGGER,
        address=device_address,
        scan_interval=scan_interval,
        device_type=device_type,
        device_data_callback=lambda device: _handle_device_update(hass, entry, device),
    )

    # Store coordinator and devices in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "devices": [],  # Will be populated as devices are discovered
        "initialized_devices": set(),  # Track which devices have entities
    }

    # Forward entry setup to sensor platform
    LOGGER.info("Setting up sensor platform for Renogy BLE device %s", device_address)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Start the coordinator after all platforms are set up
    # This ensures all entities have had a chance to subscribe to the coordinator
    LOGGER.info("Starting coordinator for Renogy BLE device %s", device_address)
    try:
        start_func = coordinator.async_start()
        entry.async_on_unload(start_func)
    except Exception as e:
        LOGGER.error("Error starting coordinator for %s: %s", device_address, e)

    # Force an immediate refresh (but not for SHUNT - it uses notifications only)
    # SHUNT devices will connect during the first refresh from async_start()
    if device_type != "SHUNT":
        LOGGER.info("Requesting initial refresh for Renogy BLE device %s", device_address)
        hass.async_create_task(coordinator.async_request_refresh())

    return True


async def _handle_device_update(
    hass: HomeAssistant, entry: ConfigEntry, device: RenogyBLEDevice
) -> None:
    """Handle device update callback."""
    LOGGER.debug("Device update for %s (%s)", device.name, device.address)

    # Make sure the device is in our registry
    if entry.entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry.entry_id]
        devices_list = entry_data.get("devices", [])

        # Check if device is already in list by address
        device_addresses = [d.address for d in devices_list]
        if device.address not in device_addresses:
            LOGGER.debug("Adding device %s to registry", device.name)
            devices_list.append(device)

            # Log the parsed data for debugging
            if device.parsed_data:
                LOGGER.debug("Device data: %s", device.parsed_data)
            else:
                LOGGER.warning("No parsed data for device %s", device.name)

        # Update the device name in the Home Assistant device registry
        # This will ensure the device name is updated in the UI
        if device.name != "Unknown Renogy Device" and not device.name.startswith(
            "Unknown"
        ):
            await update_device_registry(hass, entry, device)


async def update_device_registry(
    hass: HomeAssistant, entry: ConfigEntry, device: RenogyBLEDevice
) -> None:
    """Update device in registry."""
    try:
        device_registry = async_get_device_registry(hass)
        model = (
            device.parsed_data.get("model", device.device_type.capitalize())
            if device.parsed_data
            else device.device_type.capitalize()
        )

        # Find the device in the registry using the domain and device address
        device_entry = device_registry.async_get_device({(DOMAIN, device.address)})

        if device_entry:
            # Update the device name
            LOGGER.debug(
                "Updating device registry entry with real name: %s", device.name
            )
            device_registry.async_update_device(
                device_entry.id, name=device.name, model=model
            )
        else:
            LOGGER.debug("Device %s not found in registry for update", device.address)
    except Exception as e:
        LOGGER.error("Error updating device in registry: %s", e)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading Renogy BLE integration for %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and entry.entry_id in hass.data[DOMAIN]:
        # Stop the coordinator
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        coordinator.async_stop()

        # Remove entry from hass.data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
