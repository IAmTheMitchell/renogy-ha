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
                )
                for description in HUB_BATTERY_SENSORS
            )

        if not bank_initialized and coordinator.hub_bank is not None:
            bank_initialized = True
            new_entities.extend(
                RenogyHubBankSensor(
                    coordinator=coordinator,
                    description=description,
                )
                for description in HUB_BANK_SENSORS
            )

        if new_entities:
            async_add_entities(new_entities)

    config_entry.async_on_unload(
        coordinator.async_add_listener(_add_discovered_hub_entities)
    )
    _add_discovered_hub_entities()


class RenogyHubBatterySensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Sensor backed by one logical battery behind a Communication Hub."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: Any,
        slave_id: int,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize one validated Hub battery sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._slave_id = slave_id
        logical_id = hub_battery_identifier(coordinator.address, slave_id)

        self._attr_has_entity_name = True
        self._attr_name = cast(str | None, description.name)
        self._attr_unique_id = f"{logical_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, logical_id)},
            name=f"Renogy Hub Battery 0x{slave_id:02X}",
            manufacturer=ATTR_MANUFACTURER,
            via_device=(DOMAIN, coordinator.address),
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
    ) -> None:
        """Initialize one communicating-bank sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        logical_id = hub_bank_identifier(coordinator.address)

        self._attr_has_entity_name = True
        self._attr_name = cast(str | None, description.name)
        self._attr_unique_id = f"{logical_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, logical_id)},
            name="Renogy Hub Communicating Bank",
            manufacturer=ATTR_MANUFACTURER,
            via_device=(DOMAIN, coordinator.address),
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
