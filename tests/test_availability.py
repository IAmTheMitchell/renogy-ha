"""Tests that entity availability is governed by the device grace counter.

A single missed BLE poll (coordinator.last_update_success == False) must NOT
flip an entity to unavailable; only exhausting the device's ``max_failures``
consecutive-failure grace does. The last cached reading keeps being served for
the grace period.
"""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import MagicMock


def _install_module_stubs() -> None:
    """Install minimal Home Assistant stubs for the sensor and number modules."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    bluetooth_components_module = cast(
        Any, types.ModuleType("homeassistant.components.bluetooth")
    )
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_components_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class HomeAssistant:
        """Stub HomeAssistant class for testing."""

    def callback(func: Any) -> Any:
        """Return the function unchanged for testing."""
        return func

    core_module.HomeAssistant = HomeAssistant
    core_module.callback = callback
    sys.modules["homeassistant.core"] = core_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    passive_module = cast(
        Any,
        types.ModuleType(
            "homeassistant.components.bluetooth.passive_update_coordinator"
        ),
    )

    class PassiveBluetoothCoordinatorEntity:
        """Stub PassiveBluetoothCoordinatorEntity for testing."""

        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

    passive_module.PassiveBluetoothCoordinatorEntity = PassiveBluetoothCoordinatorEntity
    sys.modules["homeassistant.components.bluetooth.passive_update_coordinator"] = (
        passive_module
    )

    sensor_module = cast(Any, types.ModuleType("homeassistant.components.sensor"))

    class SensorEntity:
        """Stub SensorEntity class for testing."""

        @property
        def device_class(self) -> Any:
            description = getattr(self, "entity_description", None)
            return getattr(description, "device_class", None)

        @property
        def name(self) -> Any:
            return getattr(self, "_attr_name", None)

        async def async_added_to_hass(self) -> None:
            return None

        def async_write_ha_state(self) -> None:
            return None

    @dataclass(frozen=True)
    class SensorEntityDescription:
        """Stub SensorEntityDescription for testing."""

        key: str | None = None
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        suggested_display_precision: int | None = None
        entity_category: str | None = None

    class SensorDeviceClass:
        """Stub sensor device classes."""

        VOLTAGE = "voltage"
        CURRENT = "current"
        POWER = "power"
        TEMPERATURE = "temperature"
        BATTERY = "battery"
        ENERGY = "energy"

    class SensorStateClass:
        """Stub sensor state classes."""

        MEASUREMENT = "measurement"
        TOTAL_INCREASING = "total_increasing"

    sensor_module.SensorEntity = SensorEntity
    sensor_module.SensorEntityDescription = SensorEntityDescription
    sensor_module.SensorDeviceClass = SensorDeviceClass
    sensor_module.SensorStateClass = SensorStateClass
    sys.modules["homeassistant.components.sensor"] = sensor_module

    number_module = cast(Any, types.ModuleType("homeassistant.components.number"))

    class NumberEntity:
        """Stub NumberEntity class for testing."""

    @dataclass(frozen=True)
    class NumberEntityDescription:
        """Stub NumberEntityDescription for testing."""

        key: str | None = None
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        native_min_value: float | None = None
        native_max_value: float | None = None
        native_step: float | None = None
        mode: str | None = None
        entity_category: str | None = None

    class NumberDeviceClass:
        """Stub number device classes."""

        VOLTAGE = "voltage"
        CURRENT = "current"

    class NumberMode:
        """Stub number modes."""

        BOX = "box"
        SLIDER = "slider"
        AUTO = "auto"

    number_module.NumberEntity = NumberEntity
    number_module.NumberEntityDescription = NumberEntityDescription
    number_module.NumberDeviceClass = NumberDeviceClass
    number_module.NumberMode = NumberMode
    sys.modules["homeassistant.components.number"] = number_module

    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    sys.modules["homeassistant.helpers"] = helpers_module

    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )

    class DeviceInfo(dict):
        """Stub DeviceInfo that stores provided fields."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

    device_registry_module.DeviceInfo = DeviceInfo
    device_registry_module.async_get = MagicMock()
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    entity_module = cast(Any, types.ModuleType("homeassistant.helpers.entity"))

    class EntityCategory:
        """Stub entity categories."""

        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    entity_module.EntityCategory = EntityCategory
    sys.modules["homeassistant.helpers.entity"] = entity_module

    entity_platform_module = cast(
        Any, types.ModuleType("homeassistant.helpers.entity_platform")
    )

    class AddEntitiesCallback:
        """Stub AddEntitiesCallback for testing."""

    entity_platform_module.AddEntitiesCallback = AddEntitiesCallback
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_module

    restore_state_module = cast(
        Any, types.ModuleType("homeassistant.helpers.restore_state")
    )

    class ExtraStoredData:
        """Stub restore extra data base class for testing."""

        def as_dict(self) -> dict[str, Any]:
            return {}

    class RestoreEntity:
        """Stub RestoreEntity for testing."""

        async def async_added_to_hass(self) -> None:
            return None

        async def async_get_last_state(self) -> Any:
            return getattr(self, "_mock_last_state", None)

        async def async_get_last_extra_data(self) -> Any:
            return getattr(self, "_mock_last_extra_data", None)

    restore_state_module.ExtraStoredData = ExtraStoredData
    restore_state_module.RestoreEntity = RestoreEntity
    sys.modules["homeassistant.helpers.restore_state"] = restore_state_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"
    const_module.PERCENTAGE = "%"

    class Platform(str, Enum):
        """Stub Platform enum values for testing."""

        SENSOR = "sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"

    class UnitOfElectricCurrent:
        """Stub current units."""

        AMPERE = "A"

    class UnitOfElectricPotential:
        """Stub voltage units."""

        VOLT = "V"

    class UnitOfEnergy:
        """Stub energy units."""

        WATT_HOUR = "Wh"
        KILO_WATT_HOUR = "kWh"

    class UnitOfPower:
        """Stub power units."""

        WATT = "W"

    class UnitOfTemperature:
        """Stub temperature units."""

        CELSIUS = "C"

    class UnitOfTime:
        """Stub time units."""

        SECONDS = "s"
        MINUTES = "min"
        DAYS = "d"

    const_module.Platform = Platform
    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
    const_module.UnitOfEnergy = UnitOfEnergy
    const_module.UnitOfPower = UnitOfPower
    const_module.UnitOfTemperature = UnitOfTemperature
    const_module.UnitOfTime = UnitOfTime
    sys.modules["homeassistant.const"] = const_module

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyActiveBluetoothCoordinator:
        """Stub coordinator class for testing."""

    class RenogyBLEDevice:
        """Stub BLE device class for testing."""

    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    ble_module.RenogyBLEDevice = RenogyBLEDevice
    sys.modules["custom_components.renogy.ble"] = ble_module


def _load_module(name: str) -> Any:
    """Load a renogy platform module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop(f"custom_components.renogy.{name}", None)
    sys.modules.pop("custom_components.renogy", None)
    return importlib.import_module(f"custom_components.renogy.{name}")


class _GraceDevice:
    """Fake device mirroring RenogyBLEDevice's max_failures grace contract."""

    def __init__(self, parsed_data: dict[str, Any], max_failures: int = 3) -> None:
        self.address = "AA:BB:CC:DD:EE:FF"
        self.name = "Renogy Inverter"
        self.rssi = None
        self.parsed_data = parsed_data
        self.failure_count = 0
        self.max_failures = max_failures
        self.available = True

    @property
    def is_available(self) -> bool:
        return self.available and self.failure_count < self.max_failures

    def update_availability(self, success: bool) -> None:
        if success:
            self.failure_count = 0
            self.available = True
        else:
            self.failure_count += 1
            if self.failure_count >= self.max_failures and self.available:
                self.available = False


def _failed_poll_coordinator() -> MagicMock:
    """A coordinator whose most recent poll failed (last_update_success False)."""
    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = False
    coordinator.data = None
    return coordinator


def test_sensor_stays_available_through_grace_then_goes_unavailable() -> None:
    """Sensor keeps its last value until max_failures is exhausted."""
    sensor_module = _load_module("sensor")

    description = next(
        d
        for d in sensor_module.INVERTER_SENSORS
        if d.key == sensor_module.KEY_BATTERY_VOLTAGE
    )
    device = _GraceDevice({sensor_module.KEY_BATTERY_VOLTAGE: 40.0}, max_failures=3)
    coordinator = _failed_poll_coordinator()

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Inverter",
        sensor_module.DeviceType.INVERTER.value,
    )

    for failures in (1, 2):
        entity._attr_native_value = None
        device.update_availability(False)
        assert entity.available is True, f"unavailable after {failures} failure(s)"
        assert entity.native_value == 40.0

    entity._attr_native_value = None
    device.update_availability(False)  # third consecutive failure
    assert entity.available is False


def test_number_stays_available_through_grace_then_goes_unavailable() -> None:
    """Number entity honours the device grace, not last_update_success."""
    number_module = _load_module("number")

    description = next(
        d for d in number_module.DCC_ALL_NUMBERS if d.value_fn is not None
    )
    device = _GraceDevice({description.key: 25.0}, max_failures=3)
    coordinator = _failed_poll_coordinator()

    entity = number_module.RenogyNumberEntity(
        coordinator,
        device,
        description,
        number_module.DeviceType.DCC.value,
    )

    for failures in (1, 2):
        entity._attr_native_value = None
        device.update_availability(False)
        assert entity.available is True, f"unavailable after {failures} failure(s)"
        assert entity.native_value == 25.0

    entity._attr_native_value = None
    device.update_availability(False)  # third consecutive failure
    assert entity.available is False
