"""Tests for Renogy BLE integration setup behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock


def _install_module_stubs(*, install_ble: bool = True) -> type | None:
    """Install minimal module stubs to import the integration module."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"

    class Platform(str, Enum):
        """Stub Platform enum values for testing."""

        SENSOR = "sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"

    const_module.Platform = Platform
    sys.modules["homeassistant.const"] = const_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))
    core_module.HomeAssistant = object
    sys.modules["homeassistant.core"] = core_module

    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    sys.modules["homeassistant.helpers"] = helpers_module

    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )
    device_registry_module.async_get = MagicMock()
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    if not install_ble:
        sys.modules.pop("custom_components.renogy.ble", None)
        return None

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyActiveBluetoothCoordinator:
        """Stub coordinator that records its initialization args."""

        last_init: dict[str, Any] | None = None

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            type(self).last_init = kwargs

        def async_start(self):
            """Return an unload callback."""
            return lambda: None

        async def async_request_refresh(self) -> None:
            """Allow setup to schedule an initial refresh."""

        def async_stop(self) -> None:
            """Support unload tests."""

        async def async_shutdown(self) -> None:
            """Support unload tests."""

    class RenogyBLEDevice:
        """Stub BLE device class for testing."""

    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    ble_module.RenogyBLEDevice = RenogyBLEDevice
    sys.modules["custom_components.renogy.ble"] = ble_module
    return RenogyActiveBluetoothCoordinator


def _load_init_module():
    """Load the integration module with stubs in place."""
    coordinator_class = _install_module_stubs()
    sys.modules.pop("custom_components.renogy.__init__", None)
    sys.modules.pop("custom_components.renogy", None)
    module = importlib.import_module("custom_components.renogy")
    return module, coordinator_class


def test_init_module_imports_without_ble_dependency() -> None:
    """Ensure component import does not require manifest requirements yet."""
    _install_module_stubs(install_ble=False)
    sys.modules.pop("custom_components.renogy.__init__", None)
    sys.modules.pop("custom_components.renogy", None)

    module = importlib.import_module("custom_components.renogy")

    assert module.DOMAIN == "renogy"


def test_shunt_connection_mode_defaults_to_sustained() -> None:
    """Ensure shunt entries default to sustained mode when options are unset."""
    init_module, _ = _load_init_module()
    entry = MagicMock()
    entry.data = {init_module.CONF_DEVICE_TYPE: init_module.DeviceType.SHUNT300.value}
    entry.options = {}

    assert init_module._get_shunt_connection_mode(entry) == "sustained"


def test_non_shunt_connection_mode_defaults_to_intermittent() -> None:
    """Ensure non-shunt entries default to intermittent mode when unset."""
    init_module, _ = _load_init_module()
    entry = MagicMock()
    entry.data = {init_module.CONF_DEVICE_TYPE: init_module.DeviceType.CONTROLLER.value}
    entry.options = {}

    assert init_module._get_non_shunt_connection_mode(entry) == "intermittent"


def test_async_setup_entry_uses_configured_shunt_connection_mode() -> None:
    """Ensure setup passes the selected shunt mode into the coordinator."""
    init_module, coordinator_class = _load_init_module()
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        init_module.CONF_DEVICE_TYPE: init_module.DeviceType.SHUNT300.value,
        init_module.CONF_SCAN_INTERVAL: 30,
    }
    entry.options = {init_module.CONF_SHUNT_CONNECTION_MODE: "intermittent"}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()

    result = asyncio.run(init_module.async_setup_entry(hass, entry))

    assert result is True
    assert coordinator_class.last_init is not None
    assert coordinator_class.last_init["shunt_connection_mode"] == "intermittent"
    entry.add_update_listener.assert_called_once()


def test_async_setup_entry_uses_configured_non_shunt_connection_mode() -> None:
    """Ensure setup passes the selected non-shunt mode into the coordinator."""
    init_module, coordinator_class = _load_init_module()
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)

    entry = MagicMock()
    entry.entry_id = "entry-1"
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        init_module.CONF_DEVICE_TYPE: init_module.DeviceType.CONTROLLER.value,
        init_module.CONF_SCAN_INTERVAL: 30,
    }
    entry.options = {init_module.CONF_NON_SHUNT_CONNECTION_MODE: "persistent_session"}
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()

    result = asyncio.run(init_module.async_setup_entry(hass, entry))

    assert result is True
    assert coordinator_class.last_init is not None
    assert (
        coordinator_class.last_init["non_shunt_connection_mode"] == "persistent_session"
    )
    entry.add_update_listener.assert_called_once()


def test_reload_listener_reloads_entry() -> None:
    """Ensure option updates trigger a config-entry reload."""
    init_module, _ = _load_init_module()
    hass = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    entry = MagicMock()
    entry.entry_id = "entry-1"

    asyncio.run(init_module._async_reload_entry(hass, entry))

    hass.config_entries.async_reload.assert_awaited_once_with("entry-1")


def test_async_unload_entry_schedules_shutdown() -> None:
    """Ensure unload stops immediately and schedules shutdown in the background."""
    init_module, _ = _load_init_module()
    coordinator = MagicMock(async_shutdown=AsyncMock())
    hass = MagicMock()
    hass.data = {
        init_module.DOMAIN: {
            "entry-1": {
                "coordinator": coordinator,
                "devices": [],
                "initialized_devices": set(),
            }
        }
    }
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.async_create_task = MagicMock()

    entry = MagicMock()
    entry.entry_id = "entry-1"

    result = asyncio.run(init_module.async_unload_entry(hass, entry))

    assert result is True
    assert init_module.DOMAIN in hass.data
    assert "entry-1" not in hass.data[init_module.DOMAIN]
    coordinator.async_stop.assert_called_once_with()
    coordinator.async_shutdown.assert_not_awaited()
    hass.async_create_task.assert_called_once()
    shutdown_coro = hass.async_create_task.call_args.args[0]
    shutdown_coro.close()


def test_async_shutdown_coordinator_times_out() -> None:
    """Ensure coordinator shutdown timeouts are logged and do not raise."""
    init_module, _ = _load_init_module()

    async def never_finishes() -> None:
        await asyncio.Future()

    coordinator = MagicMock(async_shutdown=AsyncMock(side_effect=never_finishes))
    init_module.LOGGER.warning = MagicMock()

    asyncio.run(init_module._async_shutdown_coordinator(coordinator, "entry-1"))

    coordinator.async_shutdown.assert_awaited_once()
    init_module.LOGGER.warning.assert_called_once()
