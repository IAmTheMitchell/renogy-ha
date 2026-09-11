"""Tests for the battery-type select on charge controllers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from tests.test_number import _load_select_module


def _battery_select(select_module, device_type: str, data: dict | None = None):
    coordinator = MagicMock(address="AA:BB:CC:DD:EE:FF", data=data or {})
    coordinator.device = None
    coordinator.async_write_register = AsyncMock(return_value=True)
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
    keys = [d.key for d in select_module.CONTROLLER_SELECT_ENTITIES]
    assert keys == ["battery_type"]


def test_controller_sealed_writes_2_to_register_e004() -> None:
    """Sealed (AGM) is code 2 on a controller, at 0xE004 -- the register the
    integration's own write helper names as the battery-type register."""
    select_module = _load_select_module()
    entity, coordinator = _battery_select(
        select_module, select_module.DeviceType.CONTROLLER.value
    )

    asyncio.run(entity.async_select_option("Sealed (AGM)"))

    coordinator.async_write_register.assert_awaited_once_with(0xE004, 2)
    assert entity.current_option == "Sealed (AGM)"


def test_custom_differs_between_controller_and_dcc() -> None:
    """The one place the two value maps disagree. Reusing the DCC map on a
    controller would write 0, which is not a valid controller profile."""
    select_module = _load_select_module()

    ctrl, ctrl_coord = _battery_select(
        select_module, select_module.DeviceType.CONTROLLER.value
    )
    asyncio.run(ctrl.async_select_option("Custom"))
    ctrl_coord.async_write_register.assert_awaited_once_with(0xE004, 5)

    dcc, dcc_coord = _battery_select(select_module, select_module.DeviceType.DCC.value)
    asyncio.run(dcc.async_select_option("Custom"))
    dcc_coord.async_write_register.assert_awaited_once_with(0xE004, 0)


def test_controller_reads_the_parsers_string_and_its_own_int_codes() -> None:
    """renogy-ble reports the controller's battery type as a string ("gel");
    an int must decode through the CONTROLLER map, where 5 is custom."""
    select_module = _load_select_module()
    entity, _ = _battery_select(
        select_module,
        select_module.DeviceType.CONTROLLER.value,
        {"battery_type": "gel"},
    )
    assert entity.current_option == "Gel"

    entity, _ = _battery_select(
        select_module, select_module.DeviceType.CONTROLLER.value, {"battery_type": 5}
    )
    assert entity.current_option == "Custom"


def test_failed_write_does_not_lie_about_the_current_option() -> None:
    select_module = _load_select_module()
    entity, coordinator = _battery_select(
        select_module,
        select_module.DeviceType.CONTROLLER.value,
        {"battery_type": "gel"},
    )
    coordinator.async_write_register = AsyncMock(return_value=False)

    asyncio.run(entity.async_select_option("Sealed (AGM)"))

    assert entity.current_option == "Gel"
