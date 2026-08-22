"""Tests for Renogy BLE writable number entities."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock


def _install_module_stubs() -> None:
    """Install minimal Home Assistant module stubs to import the number module."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    sys.modules["homeassistant.components"] = components_module

    number_module = cast(Any, types.ModuleType("homeassistant.components.number"))

    class NumberEntity:
        """Stub number entity base class for testing."""

    @dataclass(frozen=True)
    class NumberEntityDescription:
        """Stub number entity description for testing."""

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

        CURRENT = "current"
        VOLTAGE = "voltage"

    class NumberMode:
        """Stub number input modes."""

        BOX = "box"

    number_module.NumberEntity = NumberEntity
    number_module.NumberEntityDescription = NumberEntityDescription
    number_module.NumberDeviceClass = NumberDeviceClass
    number_module.NumberMode = NumberMode
    sys.modules["homeassistant.components.number"] = number_module

    select_module = cast(Any, types.ModuleType("homeassistant.components.select"))

    class SelectEntity:
        """Stub select entity base class for testing."""

    @dataclass(frozen=True)
    class SelectEntityDescription:
        """Stub select entity description for testing."""

        key: str | None = None
        name: str | None = None
        entity_category: str | None = None

    select_module.SelectEntity = SelectEntity
    select_module.SelectEntityDescription = SelectEntityDescription
    sys.modules["homeassistant.components.select"] = select_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub config entry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"

    class Platform(str, Enum):
        """Stub platform enum values."""

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

    class UnitOfTime:
        """Stub time units."""

        DAYS = "d"
        MINUTES = "min"
        SECONDS = "s"

    const_module.Platform = Platform
    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
    const_module.UnitOfTime = UnitOfTime
    sys.modules["homeassistant.const"] = const_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class HomeAssistant:
        """Stub Home Assistant class for testing."""

    core_module.HomeAssistant = HomeAssistant
    sys.modules["homeassistant.core"] = core_module

    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    sys.modules["homeassistant.helpers"] = helpers_module

    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )

    class DeviceInfo(dict):
        """Stub device info that stores provided fields."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

    device_registry_module.DeviceInfo = DeviceInfo
    device_registry_module.async_get = MagicMock()
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    entity_module = cast(Any, types.ModuleType("homeassistant.helpers.entity"))

    class EntityCategory:
        """Stub entity categories."""

        CONFIG = "config"

    entity_module.EntityCategory = EntityCategory
    sys.modules["homeassistant.helpers.entity"] = entity_module

    entity_platform_module = cast(
        Any, types.ModuleType("homeassistant.helpers.entity_platform")
    )

    class AddEntitiesCallback:
        """Stub add entities callback for testing."""

    entity_platform_module.AddEntitiesCallback = AddEntitiesCallback
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_module

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


def _load_select_module() -> Any:
    """Load the select module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.select", None)
    sys.modules.pop("custom_components.renogy", None)
    return importlib.import_module("custom_components.renogy.select")


def test_unresolved_writable_entities_preserve_legacy_object_ids() -> None:
    """Modern names should retain legacy IDs until the device name resolves."""
    number_module = _load_number_module()
    coordinator = MagicMock(address="AA:BB:CC:DD:EE:FF", data={})
    description = next(
        item
        for item in number_module.DCC_OTHER_NUMBERS
        if item.key == "solar_cutoff_current"
    )
    number = number_module.RenogyNumberEntity(
        coordinator,
        None,
        description,
        number_module.DeviceType.DCC.value,
    )

    assert number._attr_has_entity_name is True
    assert number._attr_name == "Solar Cutoff Current"
    assert number.suggested_object_id == "Renogy Solar Cutoff Current"

    select_module = _load_select_module()
    selects = (
        select_module.RenogyBatteryTypeSelect,
        select_module.RenogyMaxCurrentSelect,
    )
    for entity_class, select_description in zip(
        selects, select_module.DCC_SELECT_ENTITIES, strict=True
    ):
        entity = entity_class(
            coordinator,
            None,
            select_description,
            select_module.DeviceType.DCC.value,
        )
        assert entity._attr_has_entity_name is True
        assert entity._attr_name == select_description.name
        assert entity.suggested_object_id == f"Renogy {select_description.name}"


def test_number_reads_value_directly_from_description_key() -> None:
    """Number descriptions should use their key for the current value."""
    number_module = _load_number_module()
    description = next(
        description
        for description in number_module.DCC_OTHER_NUMBERS
        if description.key == "solar_cutoff_current"
    )

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.data = {"solar_cutoff_current": 7.5}

    entity = number_module.RenogyNumberEntity(
        coordinator=coordinator,
        device=None,
        description=description,
        device_type=number_module.DeviceType.DCC.value,
    )

    assert entity.native_value == 7.5


def test_solar_cutoff_current_writes_centiamps() -> None:
    """Ensure a solar cutoff value in amps is written as centiamps."""
    number_module = _load_number_module()
    description = next(
        description
        for description in number_module.DCC_OTHER_NUMBERS
        if description.key == "solar_cutoff_current"
    )

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.async_write_register = AsyncMock(return_value=True)

    entity = number_module.RenogyNumberEntity(
        coordinator=coordinator,
        device=None,
        description=description,
        device_type=number_module.DeviceType.DCC.value,
    )
    entity.async_write_ha_state = MagicMock()

    asyncio.run(entity.async_set_native_value(7.0))

    coordinator.async_write_register.assert_awaited_once_with(
        number_module.DCCRegister.SOLAR_CUTOFF_CURRENT,
        700,
    )
    assert entity.native_value == 7.0
    entity.async_write_ha_state.assert_called_once()
