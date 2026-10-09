"""Test opt-in diagnostics without reimplementing protocol parsing in HA."""

import asyncio
import importlib
import json
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.test_ble import _load_ble_module
from tests.test_config_flow import (
    _load_config_flow_module,
    _options_entry,
    _schema_default,
    _schema_keys,
)
from tests.test_init import _load_init_module
from tests.test_sensor_setup import _load_sensor_module


@pytest.mark.parametrize(
    "kind,profile,enabled,expected",
    [
        ("inverter", "RIV4835CSH1S", True, True),
        ("inverter", "RIV4835CSH1S", False, False),
        ("inverter", None, True, False),
        ("controller", "RIV4835CSH1S", True, False),
    ],
)
def test_diagnostic_poll_is_opt_in_and_model_scoped(kind, profile, enabled, expected):
    module = _load_ble_module()
    coordinator = module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=60,
        device_type=kind,
        model_hint=profile,
        inverter_diagnostics=enabled,
    )
    coordinator.device = MagicMock()
    coordinator.device.parsed_data = {"battery_voltage": 50.6}
    coordinator._read_device_data = AsyncMock(return_value=True)
    reader = AsyncMock(
        return_value={"riv_program_04": 49.2, "riv_diagnostics": {"register_reads": {}}}
    )
    coordinator._ble_client.read_inverter_diagnostics = reader
    result = asyncio.run(coordinator._async_poll_device(None))
    assert result["battery_voltage"] == 50.6
    assert ("riv_program_04" in result) is expected
    assert reader.await_count == int(expected)


def test_optional_failure_keeps_normal_poll_success_and_retry_cache():
    module = _load_ble_module()
    coordinator = module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=60,
        device_type="inverter",
        model_hint="RIV4835CSH1S",
        inverter_diagnostics=True,
    )
    cache = {"register_reads": {"20": {"read_status": "read"}}}
    coordinator._inverter_diagnostic_cache = cache
    coordinator.device = MagicMock()
    coordinator.device.parsed_data = {"battery_voltage": 50.6, "riv_program_04": 49.2}
    coordinator._read_device_data = AsyncMock(return_value=True)
    reader = AsyncMock(side_effect=RuntimeError("Connection lost"))
    coordinator._ble_client.read_inverter_diagnostics = reader
    result = asyncio.run(coordinator._async_poll_device(None))
    assert result["battery_voltage"] == 50.6
    assert "riv_program_04" not in result
    assert result["riv_diagnostic_read_status"] == "read_error"
    assert coordinator._inverter_diagnostic_cache is cache
    reader.assert_awaited_once_with(coordinator.device, previous=cache)
    coordinator._read_device_data.return_value = False
    asyncio.run(coordinator._async_poll_device(None))
    assert reader.await_count == 1


@pytest.mark.parametrize(
    "kind,profile,has_option",
    [
        ("inverter", "RIV4835CSH1S", True),
        ("inverter", "generic", False),
        ("controller", "RIV4835CSH1S", False),
    ],
)
def test_only_riv_options_offer_diagnostics(kind, profile, has_option):
    module = _load_config_flow_module()
    const = importlib.import_module("custom_components.renogy.const")
    entry = _options_entry(const, kind)
    entry.data[const.CONF_INVERTER_PROFILE] = profile
    schema = module._build_non_shunt_options_schema(entry, "intermittent", False)
    assert (const.CONF_INVERTER_DIAGNOSTICS in _schema_keys(schema)) is has_option
    if has_option:
        assert _schema_default(schema, const.CONF_INVERTER_DIAGNOSTICS) is False
        entry.options[const.CONF_INVERTER_DIAGNOSTICS] = True
        schema = module._build_non_shunt_options_schema(entry, "intermittent", False)
        assert _schema_default(schema, const.CONF_INVERTER_DIAGNOSTICS) is True


@pytest.mark.parametrize("enabled", [False, True])
def test_setup_passes_diagnostic_opt_in(enabled):
    module, coordinator_class = _load_init_module()
    hass = MagicMock(data={})
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)
    entry = MagicMock(entry_id="entry-1")
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        "device_type": "inverter",
        "inverter_profile": "RIV4835CSH1S",
    }
    entry.options = {"inverter_diagnostics": True} if enabled else {}
    assert asyncio.run(module.async_setup_entry(hass, entry)) is True
    assert coordinator_class.last_init["inverter_diagnostics"] is enabled


def test_entities_are_diagnostic_and_preserve_precision_and_zero_values():
    module = _load_sensor_module()
    coordinator = MagicMock(
        address="AA:BB:CC:DD:EE:FF",
        device=None,
        data={"riv_program_04": 49.2, "riv_fault_count": 0},
        inverter_diagnostics=False,
    )
    base = module.create_entities_helper(coordinator, None, "inverter", "RIV4835CSH1S")
    coordinator.inverter_diagnostics = True
    expanded = module.create_entities_helper(
        coordinator, None, "inverter", "RIV4835CSH1S"
    )
    assert len(expanded) - len(base) == 45
    entities = {entity.entity_description.key: entity for entity in expanded}
    setting = entities["riv_program_04"]
    assert setting.native_value == 49.2 and setting.available
    assert setting.entity_description.suggested_display_precision == 1
    assert setting.entity_description.state_class is None
    assert (
        setting.entity_description.entity_category == module.EntityCategory.DIAGNOSTIC
    )
    assert entities["riv_fault_count"].native_value == 0
    assert entities["riv_fault_count"].available
    coordinator.data = {
        "battery_voltage": 50.6,
        "riv_diagnostics": {
            "fields": {
                "riv_program_04": {
                    "read_status": "read_error",
                    "read_error": "Timeout",
                },
            }
        },
    }
    assert setting.native_value is None and not setting.available
    assert setting.extra_state_attributes["read_error"] == "Timeout"


def test_download_uses_completed_cache_and_redacts_transport_addresses():
    _load_sensor_module()
    module = importlib.import_module("custom_components.renogy.diagnostics")
    address = "AA:BB:CC:DD:EE:FF"
    entry = SimpleNamespace(
        entry_id="private-id",
        options={},
        data={
            "address": address,
            "device_name": "private-name",
            "device_type": "inverter",
            "inverter_profile": "RIV4835CSH1S",
        },
    )
    coordinator = SimpleNamespace(
        data={
            "battery_voltage": 50.6,
            "riv_program_04": 49.2,
            "riv_diagnostics": {"read_errors": {"20": f"Disconnected {address}"}},
        },
        device=SimpleNamespace(parsed_data={"battery_voltage": 0.0}),
        _ble_client=SimpleNamespace(read_inverter_diagnostics=AsyncMock()),
    )
    hass = SimpleNamespace(
        data={"renogy": {entry.entry_id: {"coordinator": coordinator}}}
    )
    result = asyncio.run(
        module.async_get_config_entry_diagnostics(cast(Any, hass), cast(Any, entry))
    )
    assert result["measurements"]["battery_voltage"] == 50.6
    assert result["decoded_diagnostics"]["riv_program_04"] == 49.2
    serialized = json.dumps(result)
    assert not any(
        token in serialized for token in [address, "private-id", "private-name"]
    )
    assert "**REDACTED**" in serialized
    coordinator._ble_client.read_inverter_diagnostics.assert_not_awaited()
