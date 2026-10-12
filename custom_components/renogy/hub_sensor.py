"""Sensors for logical batteries connected through a Renogy Communication Hub."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_MANUFACTURER, DOMAIN
from .hub import (
    RenogyHubBankState,
    RenogyHubBatteryState,
    hub_bank_identifier,
    hub_battery_identifier,
)

HUB_BATTERY_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="battery_voltage",
        name="Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_current",
        name="Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="battery_power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_remaining_capacity",
        name="Remaining Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_capacity",
        name="Nominal Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_percentage",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
)

HUB_BANK_COUNT_KEYS = frozenset(
    {"communicating_battery_count", "discovered_battery_count"}
)

HUB_BANK_EXTREME_SLAVE_ID_KEYS = {
    "battery_percentage_min": "battery_percentage_min_slave_id",
    "battery_percentage_max": "battery_percentage_max_slave_id",
    "battery_voltage_min": "battery_voltage_min_slave_id",
    "battery_voltage_max": "battery_voltage_max_slave_id",
}

HUB_BANK_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="communicating_battery_count",
        name="Communicating Battery Count",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="discovered_battery_count",
        name="Discovered Battery Count",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="battery_current",
        name="Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="battery_power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_remaining_capacity",
        name="Remaining Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_capacity",
        name="Nominal Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    SensorEntityDescription(
        key="battery_percentage",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
)

HUB_BANK_DIAGNOSTIC_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="battery_percentage_min",
        name="Minimum State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_percentage_max",
        name="Maximum State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_percentage_spread",
        name="SOC Spread",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_voltage_min",
        name="Minimum Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_voltage_max",
        name="Maximum Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_voltage_spread",
        name="Voltage Spread",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_current_spread",
        name="Current Spread",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
)


def _bank_supports_diagnostics(bank: Any) -> bool:
    """Return whether the bank state carries the Phase 2B diagnostic fields."""
    return all(
        hasattr(bank, description.key) for description in HUB_BANK_DIAGNOSTIC_SENSORS
    )


def setup_hub_battery_sensors(
    config_entry: ConfigEntry,
    coordinator: Any,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add logical Hub battery and communicating-bank sensors on discovery."""
    if getattr(coordinator, "communication_hub_enabled", False) is not True:
        return

    initialized_slave_ids: set[int] = set()
    bank_initialized = False

    parent_device: str | tuple[str, str] = (DOMAIN, coordinator.address)
    if hasattr(dr, "async_get_device_id_by_identifier"):
        # HA 2026.9 requires the parent registry ID before registering children.
        # Parent sensor registration may still be queued by async_add_entities.
        parent_device = (
            dr.async_get(coordinator.hass)
            .async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, coordinator.address)},
            )
            .id
        )

    @callback
    def _add_discovered_hub_entities() -> None:
        nonlocal bank_initialized
        new_entities: list[SensorEntity] = []
        for battery in coordinator.hub_batteries:
            if battery.slave_id in initialized_slave_ids:
                continue

            initialized_slave_ids.add(battery.slave_id)
            new_entities.extend(
                RenogyHubBatterySensor(
                    coordinator=coordinator,
                    slave_id=battery.slave_id,
                    description=description,
                    parent_device=parent_device,
                )
                for description in HUB_BATTERY_SENSORS
            )

        if not bank_initialized and coordinator.hub_bank is not None:
            bank_initialized = True
            bank_descriptions = HUB_BANK_SENSORS
            if _bank_supports_diagnostics(coordinator.hub_bank):
                bank_descriptions += HUB_BANK_DIAGNOSTIC_SENSORS
            new_entities.extend(
                RenogyHubBankSensor(
                    coordinator=coordinator,
                    description=description,
                    parent_device=parent_device,
                )
                for description in bank_descriptions
            )

        if new_entities:
            async_add_entities(new_entities)

    config_entry.async_on_unload(
        coordinator.async_add_listener(_add_discovered_hub_entities)
    )
    _add_discovered_hub_entities()


def _hub_device_info(
    logical_id: str, name: str, parent_device: str | tuple[str, str]
) -> DeviceInfo:
    """Link a logical device using the parent reference supported by HA."""
    info = DeviceInfo(
        identifiers={(DOMAIN, logical_id)},
        name=name,
        manufacturer=ATTR_MANUFACTURER,
    )
    # These keys are mutually exclusive across supported DeviceInfo versions.
    key = "via_device_id" if isinstance(parent_device, str) else "via_device"
    cast(dict[str, Any], info)[key] = parent_device
    return info


class RenogyHubBatterySensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Sensor backed by one logical battery behind a Communication Hub."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        slave_id: int,
        description: SensorEntityDescription,
        *,
        parent_device: str | tuple[str, str],
    ) -> None:
        """Initialize one validated Hub battery sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._slave_id = slave_id
        logical_id = hub_battery_identifier(coordinator.address, slave_id)

        self._attr_has_entity_name = True
        self._attr_name = cast(str | None, description.name)
        self._attr_unique_id = f"{logical_id}_{description.key}"
        self._attr_device_info = _hub_device_info(
            logical_id, f"Renogy Hub Battery 0x{slave_id:02X}", parent_device
        )

    @property
    def _battery(self) -> RenogyHubBatteryState | None:
        """Return the latest cached state for this slave ID."""
        coordinator = cast(Any, self.coordinator)
        for battery in coordinator.hub_batteries:
            if battery.slave_id == self._slave_id:
                return battery
        return None

    @property
    def available(self) -> bool:
        """Return whether the parent poll and this logical battery are available."""
        battery = self._battery
        coordinator = cast(Any, self.coordinator)
        parent_device = coordinator.device
        return bool(
            parent_device is not None
            and parent_device.is_available
            and battery is not None
            and battery.available
        )

    @property
    def native_value(self) -> float | None:
        """Return this sensor's validated value from the Hub cache."""
        battery = self._battery
        if battery is None:
            return None
        key = self.entity_description.key
        if key is None:
            return None
        value = getattr(battery, key, None)
        return float(value) if value is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose the validated Modbus slave ID for diagnostics."""
        return {"slave_id": f"0x{self._slave_id:02X}"}


class RenogyHubBankSensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Sensor derived from batteries currently communicating through the Hub."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        description: SensorEntityDescription,
        *,
        parent_device: str | tuple[str, str],
    ) -> None:
        """Initialize one communicating-bank sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        logical_id = hub_bank_identifier(coordinator.address)

        self._attr_has_entity_name = True
        self._attr_name = cast(str | None, description.name)
        self._attr_unique_id = f"{logical_id}_{description.key}"
        self._attr_device_info = _hub_device_info(
            logical_id, "Renogy Hub Communicating Bank", parent_device
        )

    @property
    def _bank(self) -> RenogyHubBankState | None:
        """Return the latest derived communicating-bank state."""
        coordinator = cast(Any, self.coordinator)
        return coordinator.hub_bank

    @property
    def available(self) -> bool:
        """Return whether this bank value can be stated from current Hub data."""
        coordinator = cast(Any, self.coordinator)
        parent_device = coordinator.device
        bank = self._bank
        if parent_device is None or not parent_device.is_available or bank is None:
            return False

        key = self.entity_description.key
        if key in HUB_BANK_COUNT_KEYS:
            return True
        if key is None:
            return False
        return getattr(bank, key, None) is not None

    @property
    def native_value(self) -> float | int | None:
        """Return this sensor's derived communicating-bank value."""
        bank = self._bank
        if bank is None:
            return None
        key = self.entity_description.key
        if key is None:
            return None
        value = getattr(bank, key, None)
        if value is None:
            return None
        if key in HUB_BANK_COUNT_KEYS:
            return int(value)
        return float(value)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose the battery producing a bank minimum or maximum."""
        bank = self._bank
        key = self.entity_description.key
        if bank is None or key is None:
            return {}

        slave_id_key = HUB_BANK_EXTREME_SLAVE_ID_KEYS.get(key)
        if slave_id_key is None:
            return {}

        slave_id = getattr(bank, slave_id_key, None)
        if slave_id is None:
            return {}
        return {"slave_id": f"0x{int(slave_id):02X}"}
