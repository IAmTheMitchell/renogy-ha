"""Tests for Communication Hub setup wiring."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

from tests.test_init import _install_module_stubs


def _load_init_module_with_hub_stub() -> tuple[Any, Any, Any]:
    """Load the integration with base and Hub coordinator stubs."""
    base_coordinator_class = _install_module_stubs()
    assert base_coordinator_class is not None

    hub_module = cast(Any, types.ModuleType("custom_components.renogy.hub_coordinator"))

    class RenogyHubBluetoothCoordinator:
        """Stub Hub coordinator that records initialization arguments."""

        last_init: dict[str, Any] | None = None

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            type(self).last_init = kwargs

        def async_start(self):
            """Return an unload callback."""
            return lambda: None

        async def async_request_refresh(self) -> None:
            """Allow setup to schedule an initial refresh."""

        def async_stop(self) -> None:
            """Support unload behavior."""

        async def async_shutdown(self) -> None:
            """Support shutdown behavior."""

    hub_module.RenogyHubBluetoothCoordinator = RenogyHubBluetoothCoordinator
    sys.modules["custom_components.renogy.hub_coordinator"] = hub_module

    sys.modules.pop("custom_components.renogy.__init__", None)
    sys.modules.pop("custom_components.renogy", None)
    module = importlib.import_module("custom_components.renogy")
    return module, base_coordinator_class, RenogyHubBluetoothCoordinator


def _entry(module: Any, *, device_type: str, hub_enabled: bool) -> MagicMock:
    """Build a config-entry stub for Hub setup tests."""
    entry = MagicMock()
    entry.entry_id = "entry-hub"
    entry.data = {
        "address": "F0:F8:F2:57:47:0D",
        module.CONF_DEVICE_TYPE: device_type,
        module.CONF_SCAN_INTERVAL: 60,
    }
    entry.options = {
        module.CONF_COMMUNICATION_HUB_ENABLED: hub_enabled,
    }
    entry.add_update_listener = MagicMock(return_value=lambda: None)
    entry.async_on_unload = MagicMock()
    return entry


def test_communication_hub_defaults_to_disabled() -> None:
    """Existing non-shunt entries must keep Hub polling disabled by default."""
    module, _base, _hub = _load_init_module_with_hub_stub()
    entry = MagicMock()
    entry.data = {module.CONF_DEVICE_TYPE: module.DeviceType.INVERTER.value}
    entry.options = {}

    assert module._get_communication_hub_enabled(entry) is False


def test_communication_hub_option_is_ignored_for_shunt() -> None:
    """Smart Shunt entries must never enable Communication Hub polling."""
    module, _base, _hub = _load_init_module_with_hub_stub()
    entry = MagicMock()
    entry.data = {module.CONF_DEVICE_TYPE: module.DeviceType.SHUNT300.value}
    entry.options = {module.CONF_COMMUNICATION_HUB_ENABLED: True}

    assert module._get_communication_hub_enabled(entry) is False


def test_communication_hub_option_enables_hub_coordinator() -> None:
    """An enabled non-shunt entry should use the Hub-aware coordinator."""
    module, base_class, hub_class = _load_init_module_with_hub_stub()
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)
    entry = _entry(
        module,
        device_type=module.DeviceType.INVERTER.value,
        hub_enabled=True,
    )

    result = asyncio.run(module.async_setup_entry(hass, entry))

    assert result is True
    assert hub_class.last_init is not None
    assert hub_class.last_init["communication_hub_enabled"] is True
    assert hub_class.last_init["max_failures"] == module.DEFAULT_MAX_FAILURES
    assert (
        hub_class.last_init["unavailable_retry_interval"]
        == module.DEFAULT_UNAVAILABLE_RETRY_INTERVAL
    )
    assert base_class.last_init is None
    assert isinstance(
        hass.data[module.DOMAIN][entry.entry_id]["coordinator"],
        hub_class,
    )


def test_disabled_hub_keeps_existing_base_coordinator() -> None:
    """A disabled Hub option should preserve the existing coordinator path."""
    module, base_class, hub_class = _load_init_module_with_hub_stub()
    hass = MagicMock()
    hass.data = {}
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.async_create_task = lambda coro: asyncio.get_running_loop().create_task(coro)
    entry = _entry(
        module,
        device_type=module.DeviceType.INVERTER.value,
        hub_enabled=False,
    )

    result = asyncio.run(module.async_setup_entry(hass, entry))

    assert result is True
    assert base_class.last_init is not None
    assert hub_class.last_init is None
    assert isinstance(
        hass.data[module.DOMAIN][entry.entry_id]["coordinator"],
        base_class,
    )
