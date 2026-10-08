"""Tests for the battery-type select on charge controllers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from tests.test_number import _load_select_module


def _battery_select(select_module, device_type: str, data: dict | None = None):
    coordinator = MagicMock(address="AA:BB:CC:DD:EE:FF", data=data or {})
    coordinator.device = None
    coordinator.async_write_setting = AsyncMock(return_value=True)
    entity = select_module.RenogyBatteryTypeSelect(
        coordinator,
        None,
        select_module.BATTERY_TYPE_DESCRIPTION,
        device_type,
    )
    entity.async_write_ha_state = MagicMock()
    return entity, coordinator


def test_controller_gets_a_battery_type_select_but_not_max_current() -> None:
    """A Rover exposes the battery profile; max charging current is DCC-only."""
    select_module = _load_select_module()
    coordinator = MagicMock(address="AA:BB:CC:DD:EE:FF", device=None)
    entry = MagicMock(entry_id="controller", data={"device_type": "controller"})
    hass = MagicMock()
    hass.data = {select_module.DOMAIN: {entry.entry_id: {"coordinator": coordinator}}}
    add_entities = MagicMock()

    asyncio.run(select_module.async_setup_entry(hass, entry, add_entities))

    entities = add_entities.call_args.args[0]
    assert [entity.entity_description.key for entity in entities] == ["battery_type"]
    assert isinstance(entities[0], select_module.RenogyBatteryTypeSelect)


def test_controller_sealed_writes_semantic_value() -> None:
    """Pass the semantic battery type to the coordinator."""
    select_module = _load_select_module()
    entity, coordinator = _battery_select(
        select_module, select_module.DeviceType.CONTROLLER.value
    )

    asyncio.run(entity.async_select_option("Sealed (AGM)"))

    coordinator.async_write_setting.assert_awaited_once_with("battery_type", "sealed")
    assert entity.current_option == "Sealed (AGM)"


def test_custom_is_semantic_for_controller_and_dcc() -> None:
    """HA passes the same native value for both device profiles."""
    select_module = _load_select_module()

    ctrl, ctrl_coord = _battery_select(
        select_module, select_module.DeviceType.CONTROLLER.value
    )
    asyncio.run(ctrl.async_select_option("Custom"))
    ctrl_coord.async_write_setting.assert_awaited_once_with("battery_type", "custom")

    dcc, dcc_coord = _battery_select(select_module, select_module.DeviceType.DCC.value)
    asyncio.run(dcc.async_select_option("Custom"))
    dcc_coord.async_write_setting.assert_awaited_once_with("battery_type", "custom")


def test_controller_reads_parser_strings() -> None:
    """The adopted library contract publishes normalized battery types."""
    select_module = _load_select_module()
    entity, _ = _battery_select(
        select_module,
        select_module.DeviceType.CONTROLLER.value,
        {"battery_type": "gel"},
    )
    assert entity.current_option == "Gel"

    entity, _ = _battery_select(
        select_module,
        select_module.DeviceType.CONTROLLER.value,
        {"battery_type": "custom"},
    )
    assert entity.current_option == "Custom"


def test_failed_write_does_not_lie_about_the_current_option() -> None:
    select_module = _load_select_module()
    entity, coordinator = _battery_select(
        select_module,
        select_module.DeviceType.CONTROLLER.value,
        {"battery_type": "gel"},
    )
    coordinator.async_write_setting = AsyncMock(return_value=False)

    asyncio.run(entity.async_select_option("Sealed (AGM)"))

    assert entity.current_option == "Gel"


def test_max_current_preserves_options_identity_and_native_calls():
    module = _load_select_module()
    coordinator = MagicMock(
        address="AA:BB:CC:DD:EE:FF", data={"max_charging_current": 20}
    )
    coordinator.device = None
    coordinator.async_write_setting = AsyncMock(return_value=False)
    entity = module.RenogyMaxCurrentSelect(
        coordinator, None, module.DCC_SELECT_ENTITIES[1], "dcc"
    )
    entity.async_write_ha_state = MagicMock()
    assert entity._attr_unique_id == "AA:BB:CC:DD:EE:FF_max_charging_current"
    assert entity._attr_options == ["10A", "20A", "30A", "40A", "50A", "60A"]
    asyncio.run(entity.async_select_option("40A"))
    coordinator.async_write_setting.assert_awaited_once_with("max_charging_current", 40)
    assert entity.current_option == "20A"
    entity.async_write_ha_state.assert_not_called()
    coordinator.async_write_setting.return_value = True
    asyncio.run(entity.async_select_option("40A"))
    assert entity.current_option == "40A"
    coordinator.data = {"max_charging_current": 30}
    entity._handle_coordinator_update()
    assert entity.current_option == "30A"


def test_battery_select_preserves_options_and_identity():
    module = _load_select_module()
    entity, _ = _battery_select(module, "controller")
    assert entity._attr_unique_id == "AA:BB:CC:DD:EE:FF_battery_type"
    assert entity._attr_options == [
        "Custom",
        "Open (Flooded)",
        "Sealed (AGM)",
        "Gel",
        "Lithium",
    ]
