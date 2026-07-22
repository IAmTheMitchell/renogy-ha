"""Tests for Renogy BLE number entity setup behavior."""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import MagicMock


def _install_module_stubs() -> None:
    """Install minimal Home Assistant module stubs to import the number module."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    sys.modules["homeassistant.components"] = components_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class HomeAssistant:
        """Stub HomeAssistant class for testing."""

    core_module.HomeAssistant = HomeAssistant
    sys.modules["homeassistant.core"] = core_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

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

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"

    class Platform(str, Enum):
        """Stub Platform enum values for testing."""

        SENSOR = "sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"

    const_module.Platform = Platform

    class UnitOfElectricCurrent:
        """Stub current units."""

        AMPERE = "A"

    class UnitOfElectricPotential:
        """Stub voltage units."""

        VOLT = "V"

    class UnitOfTime:
        """Stub time units."""

        SECONDS = "s"
        MINUTES = "min"
        DAYS = "d"

    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
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


def _load_number_module() -> Any:
    """Load the number module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.number", None)
    sys.modules.pop("custom_components.renogy", None)
    return importlib.import_module("custom_components.renogy.number")


def test_inverter_numbers_cover_registers() -> None:
    """Ensure REGO inverter setpoints are exposed with the correct registers/ranges."""
    number = _load_number_module()

    by_key = {d.key: d for d in number.INVERTER_ALL_NUMBERS}
    assert set(by_key) == {
        "inverter_ac_input_current_limit",
        "inverter_charge_current",
        "inverter_low_voltage_warn",
        "inverter_over_voltage",
    }
    assert by_key["inverter_ac_input_current_limit"].register == 0x1168
    assert by_key["inverter_ac_input_current_limit"].scale == 10.0
    assert by_key["inverter_charge_current"].register == 0x1146
    assert by_key["inverter_low_voltage_warn"].register == 0x114E
    assert by_key["inverter_over_voltage"].register == 0x1164
    # every setpoint writes with x10 scale
    assert all(d.scale == 10.0 for d in number.INVERTER_ALL_NUMBERS)
    # ranges clamped to the app's safe bounds
    acil = by_key["inverter_ac_input_current_limit"]
    assert (acil.native_min_value, acil.native_max_value) == (1.0, 50.0)
    cc = by_key["inverter_charge_current"]
    assert (cc.native_min_value, cc.native_max_value) == (1.0, 150.0)


def test_inverter_number_setup_creates_entities_for_inverter_device() -> None:
    """Ensure async_setup_entry wires up the inverter number descriptions."""
    import asyncio

    number = _load_number_module()

    coordinator = MagicMock()
    coordinator.device = None

    hass = MagicMock()
    hass.data = {number.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {number.CONF_DEVICE_TYPE: number.DeviceType.INVERTER.value}

    async_add_entities = MagicMock()

    asyncio.run(number.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_called_once()
    (created_entities,) = async_add_entities.call_args.args
    assert len(created_entities) == len(number.INVERTER_ALL_NUMBERS)
    assert {e.entity_description.key for e in created_entities} == {
        d.key for d in number.INVERTER_ALL_NUMBERS
    }
