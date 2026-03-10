"""Tests for Renogy BLE sensor setup behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch


def _install_module_stubs() -> None:
    """Install minimal Home Assistant module stubs to import the sensor module."""
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

    @dataclass
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

    const_module.Platform = Platform
    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
    const_module.UnitOfEnergy = UnitOfEnergy
    const_module.UnitOfPower = UnitOfPower
    const_module.UnitOfTemperature = UnitOfTemperature
    sys.modules["homeassistant.const"] = const_module

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyActiveBluetoothCoordinator:
        """Stub coordinator class for testing."""

    class RenogyBLEDevice:
        """Stub BLE device class for testing."""

    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    ble_module.RenogyBLEDevice = RenogyBLEDevice
    sys.modules["custom_components.renogy.ble"] = ble_module


def _load_sensor_module() -> Any:
    """Load the sensor module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.sensor", None)
    sys.modules.pop("custom_components.renogy", None)
    return importlib.import_module("custom_components.renogy.sensor")


def test_sensor_setup_does_not_wait_for_named_shunt() -> None:
    """Ensure setup skips refresh/wait loop when shunt name is already available."""
    sensor_module = _load_sensor_module()

    device = MagicMock()
    device.name = "RTMShunt300A1B2"
    device.address = "AA:BB:CC:DD:EE:FF"

    coordinator = MagicMock()
    coordinator.device = device
    coordinator.address = device.address
    coordinator.async_request_refresh = AsyncMock()

    hass = MagicMock()
    hass.data = {sensor_module.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        sensor_module.CONF_DEVICE_TYPE: sensor_module.DeviceType.SHUNT300.value
    }

    async_add_entities = MagicMock()

    with patch.object(sensor_module, "create_device_entities", return_value=[]):
        with patch.object(
            sensor_module, "create_coordinator_entities", return_value=[]
        ):
            asyncio.run(
                sensor_module.async_setup_entry(hass, config_entry, async_add_entities)
            )

    coordinator.async_request_refresh.assert_not_awaited()
    async_add_entities.assert_not_called()


def test_shunt_energy_sensor_uses_total_increasing_state_class() -> None:
    """Ensure shunt energy sensors use a valid state class for energy."""
    sensor_module = _load_sensor_module()

    shunt_energy_description = next(
        description
        for description in sensor_module.SHUNT300_SENSORS
        if description.key == sensor_module.KEY_SHUNT_ENERGY
    )

    assert (
        shunt_energy_description.device_class == sensor_module.SensorDeviceClass.ENERGY
    )
    assert (
        shunt_energy_description.state_class
        == sensor_module.SensorStateClass.TOTAL_INCREASING
    )
