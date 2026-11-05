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

import pytest


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

        _attr_options: list[str]

        @property
        def options(self) -> list[str]:
            return self._attr_options

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

    exceptions_module = cast(Any, types.ModuleType("homeassistant.exceptions"))

    class HomeAssistantError(Exception):
        """Stub Home Assistant service error."""

    exceptions_module.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_module

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


def test_solar_cutoff_current_writes_native_amps() -> None:
    """Send native amps to the semantic coordinator contract."""
    number_module = _load_number_module()
    description = next(
        description
        for description in number_module.DCC_OTHER_NUMBERS
        if description.key == "solar_cutoff_current"
    )

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.async_write_setting = AsyncMock(return_value=True)

    entity = number_module.RenogyNumberEntity(
        coordinator=coordinator,
        device=None,
        description=description,
        device_type=number_module.DeviceType.DCC.value,
    )
    entity.async_write_ha_state = MagicMock()

    asyncio.run(entity.async_set_native_value(7.0))

    coordinator.async_write_setting.assert_awaited_once_with(
        "solar_cutoff_current",
        7.0,
    )
    assert entity.native_value == 7.0
    entity.async_write_ha_state.assert_called_once()


def test_inverter_numbers_preserve_keys_and_ranges() -> None:
    """Keep existing REGO keys and presentation ranges."""
    number = _load_number_module()

    by_key = {d.key: d for d in number.INVERTER_ALL_NUMBERS}
    assert set(by_key) == {
        "inverter_ac_input_current_limit",
        "inverter_charge_current",
        "inverter_low_voltage_warn",
        "inverter_over_voltage",
    }
    # every setpoint writes with x10 scale
    # ranges clamped to the app's safe bounds
    acil = by_key["inverter_ac_input_current_limit"]
    assert (acil.native_min_value, acil.native_max_value) == (1.0, 50.0)
    cc = by_key["inverter_charge_current"]
    assert (cc.native_min_value, cc.native_max_value, cc.native_step) == (
        5.0,
        150.0,
        5.0,
    )


def test_riv4835_program_28_number_matches_validated_range() -> None:
    """Expose only the hardware-validated RIV4835 Program 28 setpoint."""
    number = _load_number_module()

    assert len(number.RIV4835CSH1S_NUMBERS) == 1
    description = number.RIV4835CSH1S_NUMBERS[0]
    assert description.key == "inverter_ac_charge_current"
    assert description.name == "Maximum AC Charging Current"
    assert (
        description.native_min_value,
        description.native_max_value,
        description.native_step,
    ) == (0.0, 40.0, 5.0)


def test_riv4835_program_28_writes_and_uses_live_readback() -> None:
    """Send native Program 28 amps and prefer subsequent device readback."""
    number = _load_number_module()
    description = number.RIV4835CSH1S_NUMBERS[0]

    coordinator = MagicMock()
    coordinator.address = "F0:F8:F2:57:47:0D"
    coordinator.device = None
    coordinator.data = {}
    coordinator.async_write_setting = AsyncMock(return_value=True)

    entity = number.RenogyNumberEntity(
        coordinator=coordinator,
        device=None,
        description=description,
        device_type=number.DeviceType.INVERTER.value,
    )
    entity.async_write_ha_state = MagicMock()

    asyncio.run(entity.async_set_native_value(10.0))

    coordinator.async_write_setting.assert_awaited_once_with(
        "inverter_ac_charge_current",
        10.0,
    )
    assert entity.native_value == 10.0

    coordinator.data = {"inverter_ac_charge_current": 5.0}
    entity._handle_coordinator_update()
    assert entity.native_value == 5.0


def test_inverter_number_setup_creates_entities_for_inverter_device() -> None:
    """Ensure async_setup_entry wires up the inverter number descriptions."""
    number = _load_number_module()

    coordinator = MagicMock()
    coordinator.device = None

    hass = MagicMock()
    hass.data = {number.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        number.CONF_DEVICE_TYPE: number.DeviceType.INVERTER.value,
        number.CONF_DEVICE_NAME: "BTRIC130000029",
    }

    async_add_entities = MagicMock()

    asyncio.run(number.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_called_once()
    (created_entities,) = async_add_entities.call_args.args
    assert len(created_entities) == len(number.INVERTER_ALL_NUMBERS)
    assert {e.entity_description.key for e in created_entities} == {
        d.key for d in number.INVERTER_ALL_NUMBERS
    }


def test_riv4835_number_setup_uses_model_profile() -> None:
    """RIV4835 entries should expose only the validated Program 28 control."""
    number = _load_number_module()

    coordinator = MagicMock()
    coordinator.device = None
    hass = MagicMock()
    hass.data = {number.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        number.CONF_DEVICE_TYPE: number.DeviceType.INVERTER.value,
        number.CONF_DEVICE_NAME: "BT-TH-F257470D",
        number.CONF_INVERTER_PROFILE: number.RIV4835CSH1S_INVERTER_PROFILE,
    }
    async_add_entities = MagicMock()

    asyncio.run(number.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_called_once()
    (created_entities,) = async_add_entities.call_args.args
    assert len(created_entities) == 1
    assert created_entities[0].entity_description is number.RIV4835CSH1S_NUMBERS[0]


def test_inverter_number_setup_skips_non_rego_inverters() -> None:
    """REGO setpoints should not be exposed on incompatible inverter profiles."""
    number = _load_number_module()

    coordinator = MagicMock()
    coordinator.device = None
    hass = MagicMock()
    hass.data = {number.DOMAIN: {"entry-1": {"coordinator": coordinator}}}
    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        number.CONF_DEVICE_TYPE: number.DeviceType.INVERTER.value,
        number.CONF_DEVICE_NAME: "RNGRIU123456",
    }
    async_add_entities = MagicMock()

    asyncio.run(number.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_not_called()


def test_failed_number_write_preserves_live_value():
    module = _load_number_module()
    coordinator = MagicMock(address="AA:BB:CC:DD:EE:FF", data={"boost_voltage": 13.8})
    coordinator.async_write_setting = AsyncMock(return_value=False)
    description = next(d for d in module.DCC_ALL_NUMBERS if d.key == "boost_voltage")
    entity = module.RenogyNumberEntity(coordinator, None, description, "dcc")
    entity.async_write_ha_state = MagicMock()
    asyncio.run(entity.async_set_native_value(14.3))
    assert entity.native_value == 13.8
    entity.async_write_ha_state.assert_not_called()


def test_number_descriptions_have_no_wire_metadata():
    module = _load_number_module()
    for description in (
        *module.DCC_ALL_NUMBERS,
        *module.INVERTER_ALL_NUMBERS,
        *module.RIV4835CSH1S_NUMBERS,
    ):
        assert not hasattr(description, "register")
        assert not hasattr(description, "scale")


def _riv_output_priority_entity(initial: str = "SBU"):
    """Build a Program 01 entity with simulated polled data."""
    select = _load_select_module()
    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.data = {"output_priority": initial}
    coordinator.async_write_setting = AsyncMock(return_value=True)

    entity = select.RenogyOutputPrioritySelect(
        coordinator,
        None,
        select.RIV_SELECT_ENTITIES[0],
        select.DeviceType.INVERTER.value,
    )
    entity.async_write_ha_state = MagicMock()
    return select, coordinator, entity


def test_riv_output_priority_profile_gating():
    """Only the explicit RIV inverter profile creates this Select."""
    select = _load_select_module()
    coordinator = MagicMock()
    coordinator.device = None
    coordinator.address = "AA:BB:CC:DD:EE:FF"

    hass = MagicMock()
    hass.data = {select.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        select.CONF_DEVICE_TYPE: select.DeviceType.INVERTER.value,
        select.CONF_INVERTER_PROFILE: select.RIV4835CSH1S_INVERTER_PROFILE,
    }

    add_entities = MagicMock()
    asyncio.run(select.async_setup_entry(hass, entry, add_entities))
    add_entities.assert_called_once()

    (entities,) = add_entities.call_args.args
    assert len(entities) == 1
    assert entities[0].entity_description.key == "output_priority"
    assert entities[0].options == ["SOL", "UTI", "SBU"]

    entry.data[select.CONF_INVERTER_PROFILE] = select.DEFAULT_INVERTER_PROFILE
    add_entities.reset_mock()
    asyncio.run(select.async_setup_entry(hass, entry, add_entities))
    add_entities.assert_not_called()


def test_riv_output_priority_uses_live_semantic_readback():
    """Show the polled state without maintaining an optimistic cache."""
    _, coordinator, entity = _riv_output_priority_entity()

    assert entity.current_option == "SBU"

    coordinator.data = {"output_priority": "SOL"}
    assert entity.current_option == "SOL"

    coordinator.data = {"output_priority": "unknown"}
    assert entity.current_option is None


def test_riv_output_priority_writes_all_options():
    """All three settings use the public semantic coordinator API."""
    _, coordinator, entity = _riv_output_priority_entity()

    async def confirmed_write(key, option):
        assert key == "output_priority"
        coordinator.data = {"output_priority": option}
        return True

    coordinator.async_write_setting = AsyncMock(side_effect=confirmed_write)

    for option in ("SOL", "UTI", "SBU"):
        asyncio.run(entity.async_select_option(option))
        assert entity.current_option == option

    assert coordinator.async_write_setting.await_count == 3
    assert entity.async_write_ha_state.call_count == 3


def test_riv_output_priority_rejects_failed_write():
    """A failed transport operation must not change the displayed mode."""
    select, coordinator, entity = _riv_output_priority_entity()

    coordinator.async_write_setting = AsyncMock(return_value=False)

    with pytest.raises(select.HomeAssistantError):
        asyncio.run(entity.async_select_option("UTI"))

    assert entity.current_option == "SBU"
    entity.async_write_ha_state.assert_not_called()


def test_riv_output_priority_rejects_mismatched_readback():
    """A successful write without matching readback is not success."""
    select, coordinator, entity = _riv_output_priority_entity()

    coordinator.async_write_setting = AsyncMock(return_value=True)

    with pytest.raises(select.HomeAssistantError):
        asyncio.run(entity.async_select_option("UTI"))

    assert entity.current_option == "SBU"
    entity.async_write_ha_state.assert_not_called()


def test_riv_output_priority_rejects_invalid_option():
    """Invalid choices never reach the BLE API."""
    select, coordinator, entity = _riv_output_priority_entity()

    with pytest.raises(select.HomeAssistantError):
        asyncio.run(entity.async_select_option("INVALID"))

    coordinator.async_write_setting.assert_not_awaited()
