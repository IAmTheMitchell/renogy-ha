"""Support for Renogy BLE writable number entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, cast

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    DCCRegister,
    DeviceType,
)


@dataclass(frozen=True)
class RenogyNumberEntityDescription(NumberEntityDescription):
    """Describes a Renogy number entity."""

    register: int = 0
    # Scale factor: device value = HA value * scale
    scale: float = 1.0


# DCC voltage parameters (all use 0.1V scale, range 7-17V for 12V system)
DCC_VOLTAGE_NUMBERS: tuple[RenogyNumberEntityDescription, ...] = (
    RenogyNumberEntityDescription(
        key="overvoltage_threshold",
        name="Overvoltage Threshold",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.OVERVOLTAGE_THRESHOLD,
        scale=10.0,  # 14.0V -> 140
    ),
    RenogyNumberEntityDescription(
        key="charging_limit_voltage",
        name="Charging Limit Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.CHARGING_LIMIT_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="equalization_voltage",
        name="Equalization Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.EQUALIZATION_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="boost_voltage",
        name="Boost Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.BOOST_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="float_voltage",
        name="Float Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.FLOAT_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="boost_return_voltage",
        name="Boost Return Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.BOOST_RETURN_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="overdischarge_return_voltage",
        name="Overdischarge Return Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.OVERDISCHARGE_RETURN_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="undervoltage_warning",
        name="Undervoltage Warning",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.UNDERVOLTAGE_WARNING,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="overdischarge_voltage",
        name="Overdischarge Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.OVERDISCHARGE_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="discharge_limit_voltage",
        name="Discharge Limit Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=7.0,
        native_max_value=17.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.DISCHARGE_LIMIT_VOLTAGE,
        scale=10.0,
    ),
    RenogyNumberEntityDescription(
        key="reverse_charging_voltage",
        name="Reverse Charging Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        native_min_value=11.0,
        native_max_value=15.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.REVERSE_CHARGING_VOLTAGE,
        scale=10.0,
    ),
)

# DCC time parameters
DCC_TIME_NUMBERS: tuple[RenogyNumberEntityDescription, ...] = (
    RenogyNumberEntityDescription(
        key="overdischarge_delay",
        name="Overdischarge Delay",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=120,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.OVERDISCHARGE_DELAY,
        scale=1.0,
    ),
    RenogyNumberEntityDescription(
        key="equalization_time",
        name="Equalization Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=0,
        native_max_value=300,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.EQUALIZATION_TIME,
        scale=1.0,
    ),
    RenogyNumberEntityDescription(
        key="boost_time",
        name="Boost Time",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=10,
        native_max_value=300,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.BOOST_TIME,
        scale=1.0,
    ),
    RenogyNumberEntityDescription(
        key="equalization_interval",
        name="Equalization Interval",
        native_unit_of_measurement=UnitOfTime.DAYS,
        native_min_value=0,
        native_max_value=255,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.EQUALIZATION_INTERVAL,
        scale=1.0,
    ),
)

# DCC other parameters
DCC_OTHER_NUMBERS: tuple[RenogyNumberEntityDescription, ...] = (
    RenogyNumberEntityDescription(
        key="temperature_compensation",
        name="Temperature Compensation",
        native_unit_of_measurement="mV/C/2V",
        native_min_value=0,
        native_max_value=5,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.TEMPERATURE_COMPENSATION,
        scale=1.0,
    ),
    RenogyNumberEntityDescription(
        key="solar_cutoff_current",
        name="Solar Cutoff Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=NumberDeviceClass.CURRENT,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        register=DCCRegister.SOLAR_CUTOFF_CURRENT,
        scale=100.0,  # 7.0A -> 700 centiamps
    ),
)

# All DCC number entities
DCC_ALL_NUMBERS = DCC_VOLTAGE_NUMBERS + DCC_TIME_NUMBERS + DCC_OTHER_NUMBERS


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE number entities."""
    LOGGER.debug(
        "Setting up Renogy BLE number entities for entry: %s", config_entry.entry_id
    )

    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    # Get device type from config
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)

    # Only create number entities for DCC devices
    if device_type != DeviceType.DCC.value:
        LOGGER.debug(
            "Skipping number entities for non-DCC device type: %s", device_type
        )
        return

    LOGGER.debug("Setting up number entities for DCC device")

    entities = []
    device = coordinator.device

    for description in DCC_ALL_NUMBERS:
        entity = RenogyNumberEntity(
            coordinator=coordinator,
            device=device,
            description=description,
            device_type=device_type,
        )
        entities.append(entity)

    if entities:
        LOGGER.debug("Adding %s number entities", len(entities))
        async_add_entities(entities)


class RenogyNumberEntity(NumberEntity):
    """Representation of a Renogy BLE number entity."""

    entity_description: RenogyNumberEntityDescription
    # Friendly name = device name + entity name, so UI device renames cascade.
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        description: RenogyNumberEntityDescription,
        device_type: str = DEFAULT_DEVICE_TYPE,
    ) -> None:
        """Initialize the number entity."""
        self.coordinator = coordinator
        self._device = device
        self.entity_description = description
        self._attr_native_value = None

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
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self._attr_native_value is not None:
            return self._attr_native_value

        data = None
        if self._device and self._device.parsed_data:
            data = self._device.parsed_data
        elif self.coordinator.data:
            data = self.coordinator.data

        if not data:
            return None

        value = data.get(self.entity_description.key)
        if value is not None:
            self._attr_native_value = float(value)
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        # Convert HA value to device value using scale
        device_value = int(value * self.entity_description.scale)

        LOGGER.info(
            "Setting %s to %s (device value: %s, register: 0x%04X)",
            self.entity_description.key,
            value,
            device_value,
            self.entity_description.register,
        )

        # Write to device via coordinator
        success = await self.coordinator.async_write_register(
            self.entity_description.register, device_value
        )

        if success:
            # Update local value
            self._attr_native_value = value
            self.async_write_ha_state()
            LOGGER.info("Successfully set %s to %s", self.entity_description.key, value)
        else:
            LOGGER.error("Failed to set %s to %s", self.entity_description.key, value)

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Clear cached value to force a refresh
        self._attr_native_value = None

        # Update device reference if needed
        if not self._device and self.coordinator.device:
            self._device = self.coordinator.device

        self.async_write_ha_state()
