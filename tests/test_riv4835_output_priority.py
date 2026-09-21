"""Tests for the RIV4835CSH1S Program 01 Output Priority select."""

from __future__ import annotations

import asyncio
import sys
import types
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, call

from tests.test_number import _load_select_module


def test_riv4835_output_priority_select_is_model_gated() -> None:
    """Expose Output Priority only for the RIV4835CSH1S inverter profile."""
    select = _load_select_module()

    coordinator = MagicMock()
    coordinator.device = None
    coordinator.address = "F0:F8:F2:57:47:0D"

    hass = MagicMock()
    hass.data = {select.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        select.CONF_DEVICE_TYPE: select.DeviceType.INVERTER.value,
        select.CONF_INVERTER_PROFILE: select.RIV4835CSH1S_INVERTER_PROFILE,
    }
    async_add_entities = MagicMock()

    asyncio.run(select.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_called_once()
    (created_entities,) = async_add_entities.call_args.args
    assert len(created_entities) == 1
    entity = created_entities[0]
    assert isinstance(entity, select.RenogyOutputPrioritySelect)
    assert entity.entity_description.key == "output_priority"
    assert entity._attr_options == ["SOL", "UTI", "SBU"]


def test_generic_inverter_does_not_get_output_priority_select() -> None:
    """Do not expose the RIV-specific control on generic inverter profiles."""
    select = _load_select_module()

    coordinator = MagicMock()
    coordinator.device = None
    coordinator.address = "AA:BB:CC:DD:EE:FF"

    hass = MagicMock()
    hass.data = {select.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        select.CONF_DEVICE_TYPE: select.DeviceType.INVERTER.value,
        select.CONF_INVERTER_PROFILE: select.DEFAULT_INVERTER_PROFILE,
    }
    async_add_entities = MagicMock()

    asyncio.run(select.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_not_called()


def test_program01_mapping_matches_hardware_validation() -> None:
    """Keep the observed Program 01 raw mapping exact."""
    select = _load_select_module()

    assert select.RIV_OUTPUT_PRIORITY_BY_RAW == {0: "SOL", 1: "UTI", 2: "SBU"}
    assert select.RIV_OUTPUT_PRIORITY_TO_RAW == {"SOL": 0, "UTI": 1, "SBU": 2}


def test_all_program01_options_are_writable() -> None:
    """Pass SOL, UTI, and SBU through to the verified transaction helper."""
    select = _load_select_module()

    exceptions_module = cast(Any, types.ModuleType("homeassistant.exceptions"))

    class HomeAssistantError(Exception):
        """Stub Home Assistant service error."""

    exceptions_module.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_module

    coordinator = MagicMock()
    coordinator.device = None
    coordinator.address = "F0:F8:F2:57:47:0D"

    entity = select.RenogyOutputPrioritySelect(
        coordinator=coordinator,
        device=None,
        description=select.RIV_SELECT_ENTITIES[0],
        device_type=select.DeviceType.INVERTER.value,
    )
    entity.async_write_ha_state = MagicMock()

    transaction_module = cast(
        Any, types.ModuleType("custom_components.renogy.riv4835_output_priority")
    )
    transaction_module.async_write_output_priority = AsyncMock(
        side_effect=lambda _coordinator, target: target
    )
    sys.modules[
        "custom_components.renogy.riv4835_output_priority"
    ] = transaction_module

    for option in ("SOL", "UTI", "SBU"):
        asyncio.run(entity.async_select_option(option))
        assert entity.current_option == option

    assert transaction_module.async_write_output_priority.await_args_list == [
        call(coordinator, 0),
        call(coordinator, 1),
        call(coordinator, 2),
    ]
