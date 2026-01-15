"""Support for Renogy BLE select entities."""

from __future__ import annotations

from typing import Optional

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DCC_BATTERY_TYPE_VALUES,
    DCC_BATTERY_TYPES,
    DCC_MAX_CURRENT_OPTIONS,
    DCC_MAX_CURRENT_TO_DEVICE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    DCCRegister,
    DeviceType,
)

# Battery type options for display
BATTERY_TYPE_OPTIONS = [
    "custom",
    "open",
    "sealed",
    "gel",
    "lithium",
]

# Human-readable names for display
BATTERY_TYPE_DISPLAY_NAMES = {
    "custom": "Custom",
    "open": "Open (Flooded)",
    "sealed": "Sealed (AGM)",
    "gel": "Gel",
    "lithium": "Lithium",
}


# Max charging current options for display (in amps)
MAX_CURRENT_OPTIONS = [f"{amp}A" for amp in DCC_MAX_CURRENT_OPTIONS]

# Mapping from display string to amps
MAX_CURRENT_DISPLAY_TO_AMPS = {f"{amp}A": amp for amp in DCC_MAX_CURRENT_OPTIONS}


DCC_SELECT_ENTITIES = (
    SelectEntityDescription(
        key="battery_type",
        name="Battery Type",
        entity_category=EntityCategory.CONFIG,
    ),
    SelectEntityDescription(
        key="max_charging_current",
        name="Max Charging Current",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE select entities."""
    LOGGER.debug(
        "Setting up Renogy BLE select entities for entry: %s", config_entry.entry_id
    )

    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    # Get device type from config
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)

    # Only create select entities for DCC devices
    if device_type != DeviceType.DCC.value:
        LOGGER.debug(
            "Skipping select entities for non-DCC device type: %s", device_type
        )
        return

    LOGGER.debug("Setting up select entities for DCC device")

    entities = []
    device = coordinator.device

    for description in DCC_SELECT_ENTITIES:
        if description.key == "battery_type":
            entity = RenogyBatteryTypeSelect(
                coordinator=coordinator,
                device=device,
                description=description,
                device_type=device_type,
            )
        elif description.key == "max_charging_current":
            entity = RenogyMaxCurrentSelect(
                coordinator=coordinator,
                device=device,
                description=description,
                device_type=device_type,
            )
        else:
            continue
        entities.append(entity)

    if entities:
        LOGGER.debug("Adding %s select entities", len(entities))
        async_add_entities(entities)


class RenogyBatteryTypeSelect(SelectEntity):
    """Representation of a Renogy battery type select entity."""

    entity_description: SelectEntityDescription

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        description: SelectEntityDescription,
        device_type: str = DEFAULT_DEVICE_TYPE,
    ) -> None:
        """Initialize the select entity."""
        self.coordinator = coordinator
        self._device = device
        self.entity_description = description
        self._device_type = device_type
        self._attr_options = list(BATTERY_TYPE_DISPLAY_NAMES.values())
        self._attr_current_option = None

        # Device-dependent properties
        if device:
            self._attr_unique_id = f"{device.address}_{description.key}"
            self._attr_name = f"{device.name} {description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=f"Renogy {device_type.upper()}",
            )
        else:
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            self._attr_name = f"Renogy {description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.upper()}",
                manufacturer=ATTR_MANUFACTURER,
            )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self._attr_current_option is not None:
            return self._attr_current_option

        data = None
        if self._device and self._device.parsed_data:
            data = self._device.parsed_data
        elif self.coordinator.data:
            data = self.coordinator.data

        if not data:
            return None

        # Get the battery type value from data
        battery_type = data.get("battery_type")
        if battery_type is None:
            return None

        # If it's already a string, convert to display name
        if isinstance(battery_type, str):
            display_name = BATTERY_TYPE_DISPLAY_NAMES.get(battery_type.lower())
            if display_name:
                self._attr_current_option = display_name
                return display_name

        # If it's an integer, convert to display name
        if isinstance(battery_type, int):
            type_key = DCC_BATTERY_TYPES.get(battery_type)
            if type_key:
                display_name = BATTERY_TYPE_DISPLAY_NAMES.get(type_key)
                if display_name:
                    self._attr_current_option = display_name
                    return display_name

        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Find the key for this display name
        type_key = None
        for key, display in BATTERY_TYPE_DISPLAY_NAMES.items():
            if display == option:
                type_key = key
                break

        if type_key is None:
            LOGGER.error("Unknown battery type option: %s", option)
            return

        # Get the device value for this type
        device_value = DCC_BATTERY_TYPE_VALUES.get(type_key)
        if device_value is None:
            LOGGER.error("No device value for battery type: %s", type_key)
            return

        LOGGER.info(
            "Setting battery type to %s (device value: %s, register: 0x%04X)",
            option,
            device_value,
            DCCRegister.BATTERY_TYPE,
        )

        # Write to device via coordinator
        success = await self.coordinator.async_write_register(
            DCCRegister.BATTERY_TYPE, device_value
        )

        if success:
            # Update local value
            self._attr_current_option = option
            self.async_write_ha_state()
            LOGGER.info("Successfully set battery type to %s", option)
        else:
            LOGGER.error("Failed to set battery type to %s", option)

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear cached value to force a refresh
        self._attr_current_option = None

        # Update device reference if needed
        if not self._device and self.coordinator.device:
            self._device = self.coordinator.device

        self.async_write_ha_state()


class RenogyMaxCurrentSelect(SelectEntity):
    """Representation of a Renogy max charging current select entity."""

    entity_description: SelectEntityDescription

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        description: SelectEntityDescription,
        device_type: str = DEFAULT_DEVICE_TYPE,
    ) -> None:
        """Initialize the select entity."""
        self.coordinator = coordinator
        self._device = device
        self.entity_description = description
        self._device_type = device_type
        self._attr_options = MAX_CURRENT_OPTIONS
        self._attr_current_option = None

        # Device-dependent properties
        if device:
            self._attr_unique_id = f"{device.address}_{description.key}"
            self._attr_name = f"{device.name} {description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=f"Renogy {device_type.upper()}",
            )
        else:
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            self._attr_name = f"Renogy {description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.upper()}",
                manufacturer=ATTR_MANUFACTURER,
            )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        if self._attr_current_option is not None:
            return self._attr_current_option

        data = None
        if self._device and self._device.parsed_data:
            data = self._device.parsed_data
        elif self.coordinator.data:
            data = self.coordinator.data

        if not data:
            return None

        # Get the max charging current value from data (in amps after scale)
        current_amps = data.get("max_charging_current")
        if current_amps is None:
            return None

        # Convert to integer and find closest valid option
        try:
            current_int = int(round(float(current_amps)))
            # Find the closest valid option
            if current_int in DCC_MAX_CURRENT_OPTIONS:
                display = f"{current_int}A"
                self._attr_current_option = display
                return display
        except (ValueError, TypeError):
            pass

        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get the amp value from display string
        amp_value = MAX_CURRENT_DISPLAY_TO_AMPS.get(option)
        if amp_value is None:
            LOGGER.error("Unknown max current option: %s", option)
            return

        # Get the device value (centiamps)
        device_value = DCC_MAX_CURRENT_TO_DEVICE.get(amp_value)
        if device_value is None:
            LOGGER.error("No device value for current: %sA", amp_value)
            return

        LOGGER.info(
            "Setting max charging current to %s (device value: %s, register: 0x%04X)",
            option,
            device_value,
            DCCRegister.MAX_CHARGING_CURRENT,
        )

        # Write to device via coordinator
        success = await self.coordinator.async_write_register(
            DCCRegister.MAX_CHARGING_CURRENT, device_value
        )

        if success:
            # Update local value
            self._attr_current_option = option
            self.async_write_ha_state()
            LOGGER.info("Successfully set max charging current to %s", option)
        else:
            LOGGER.error("Failed to set max charging current to %s", option)

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear cached value to force a refresh
        self._attr_current_option = None

        # Update device reference if needed
        if not self._device and self.coordinator.device:
            self._device = self.coordinator.device

        self.async_write_ha_state()
