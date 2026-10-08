"""Support for Renogy BLE select entities."""

from __future__ import annotations

from typing import Optional, cast

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from renogy_ble import get_device_settings

from .availability import is_entity_available
from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    DeviceType,
)

# Human-readable names for display
BATTERY_TYPE_DISPLAY_NAMES = {
    "custom": "Custom",
    "open": "Open (Flooded)",
    "sealed": "Sealed (AGM)",
    "gel": "Gel",
    "lithium": "Lithium",
}


# Capabilities contain native values; display formatting remains in HA.
DCC_MAX_CURRENT_OPTIONS = next(
    cap.options
    for cap in get_device_settings("dcc")
    if cap.key == "max_charging_current"
)
# Max charging current options for display (in amps)
MAX_CURRENT_OPTIONS = [f"{amp}A" for amp in DCC_MAX_CURRENT_OPTIONS]

# Mapping from display string to amps
MAX_CURRENT_DISPLAY_TO_AMPS = {f"{amp}A": amp for amp in DCC_MAX_CURRENT_OPTIONS}


BATTERY_TYPE_DESCRIPTION = SelectEntityDescription(
    key="battery_type",
    name="Battery Type",
    entity_category=EntityCategory.CONFIG,
)

DCC_SELECT_ENTITIES = (
    BATTERY_TYPE_DESCRIPTION,
    SelectEntityDescription(
        key="max_charging_current",
        name="Max Charging Current",
        entity_category=EntityCategory.CONFIG,
    ),
)

CONTROLLER_SELECT_ENTITIES = (BATTERY_TYPE_DESCRIPTION,)


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

    # Select entities exist for the device types that have a writable profile.
    if device_type == DeviceType.DCC.value:
        descriptions = DCC_SELECT_ENTITIES
    elif device_type == DeviceType.CONTROLLER.value:
        descriptions = CONTROLLER_SELECT_ENTITIES
    else:
        LOGGER.debug("Skipping select entities for device type: %s", device_type)
        return

    LOGGER.debug("Setting up select entities for %s device", device_type)

    entities = []
    device = coordinator.device

    for description in descriptions:
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
    # Friendly name = device name + entity name, so UI device renames cascade.
    _attr_has_entity_name = True

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
        self._attr_options = list(BATTERY_TYPE_DISPLAY_NAMES.values())
        self._attr_current_option = None
        # Device-dependent properties
        if device:
            self._attr_unique_id = f"{device.address}_{description.key}"
            self._attr_name = cast("str | None", description.name)
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=f"Renogy {device_type.upper()}",
            )
        else:
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            self._attr_name = cast("str | None", description.name)
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.upper()}",
                manufacturer=ATTR_MANUFACTURER,
            )

    @property
    def suggested_object_id(self) -> str | None:
        """Preserve the legacy entity component before name resolution."""
        if self._device is None:
            return f"Renogy {self._attr_name}"
        return super().suggested_object_id

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return is_entity_available(self.coordinator, self._device)

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

        success = await self.coordinator.async_write_setting("battery_type", type_key)

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
    # Friendly name = device name + entity name, so UI device renames cascade.
    _attr_has_entity_name = True

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
        self._attr_options = MAX_CURRENT_OPTIONS
        self._attr_current_option = None

        # Device-dependent properties
        if device:
            self._attr_unique_id = f"{device.address}_{description.key}"
            self._attr_name = cast("str | None", description.name)
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=f"Renogy {device_type.upper()}",
            )
        else:
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            self._attr_name = cast("str | None", description.name)
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.upper()}",
                manufacturer=ATTR_MANUFACTURER,
            )

    @property
    def suggested_object_id(self) -> str | None:
        """Preserve the legacy entity component before name resolution."""
        if self._device is None:
            return f"Renogy {self._attr_name}"
        return super().suggested_object_id

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return is_entity_available(self.coordinator, self._device)

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
        except ValueError, TypeError:
            pass

        return None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get the amp value from display string
        amp_value = MAX_CURRENT_DISPLAY_TO_AMPS.get(option)
        if amp_value is None:
            LOGGER.error("Unknown max current option: %s", option)
            return

        success = await self.coordinator.async_write_setting(
            "max_charging_current", amp_value
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
