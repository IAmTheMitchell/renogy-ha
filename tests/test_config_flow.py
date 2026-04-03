"""Tests for Renogy BLE config-flow behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock


def _load_config_flow_module() -> Any:
    """Load config_flow with minimal Home Assistant stubs."""
    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg

    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    sys.modules["homeassistant.components"] = components_module

    bluetooth_module = cast(Any, types.ModuleType("homeassistant.components.bluetooth"))

    class BluetoothServiceInfoBleak:
        """Stub BluetoothServiceInfoBleak for config-flow tests."""

        def __init__(
            self,
            address: str,
            name: str | None,
            manufacturer_data: dict[int, bytes] | None = None,
        ) -> None:
            """Initialize the bluetooth discovery object."""
            self.address = address
            self.name = name
            self.device = MagicMock()
            self.device.address = address
            self.device.name = name
            self.device.rssi = -60
            self.advertisement = MagicMock()
            self.advertisement.rssi = -60
            self.advertisement.manufacturer_data = manufacturer_data or {}

    bluetooth_module.BluetoothServiceInfoBleak = BluetoothServiceInfoBleak
    bluetooth_module.async_discovered_service_info = MagicMock(return_value=[])
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_module
    components_module.bluetooth = bluetooth_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for config-flow imports."""

    class ConfigFlow:
        """Stub ConfigFlow with the methods used by this integration."""

        def __init_subclass__(cls, *, domain: str | None = None, **kwargs: Any) -> None:
            """Accept Home Assistant's domain keyword during subclassing."""
            super().__init_subclass__(**kwargs)
            cls.domain = domain

        def __init__(self) -> None:
            """Initialize config-flow state."""
            self.context: dict[str, Any] = {}

        async def async_set_unique_id(
            self, unique_id: str, raise_on_progress: bool = True
        ) -> None:
            """Record the unique ID for the flow."""
            self.unique_id = unique_id
            self.raise_on_progress = raise_on_progress

        def _abort_if_unique_id_configured(self) -> None:
            """Pretend no existing entry is configured."""

        def async_show_form(
            self,
            *,
            step_id: str,
            data_schema: Any,
            description_placeholders: dict[str, str] | None = None,
            errors: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            """Return a Home Assistant-like form result."""
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "description_placeholders": description_placeholders or {},
                "errors": errors or {},
            }

        def async_create_entry(self, *, title: str, data: Any) -> dict[str, Any]:
            """Return a Home Assistant-like create-entry result."""
            return {"type": "create_entry", "title": title, "data": data}

        def async_abort(
            self,
            *,
            reason: str,
            description_placeholders: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            """Return a Home Assistant-like abort result."""
            return {
                "type": "abort",
                "reason": reason,
                "description_placeholders": description_placeholders or {},
            }

    class OptionsFlow:
        """Stub OptionsFlow for config-flow imports."""

        def async_show_form(self, *, step_id: str, data_schema: Any) -> dict[str, Any]:
            """Return a Home Assistant-like options-form result."""
            return {"type": "form", "step_id": step_id, "data_schema": data_schema}

        def async_create_entry(self, *, title: str, data: Any) -> dict[str, Any]:
            """Return a Home Assistant-like options-entry result."""
            return {"type": "create_entry", "title": title, "data": data}

    config_entries_module.ConfigEntry = ConfigEntry
    config_entries_module.ConfigFlow = ConfigFlow
    config_entries_module.ConfigFlowResult = dict[str, Any]
    config_entries_module.OptionsFlow = OptionsFlow
    sys.modules["homeassistant.config_entries"] = config_entries_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"
    const_module.CONF_SCAN_INTERVAL = "scan_interval"
    sys.modules["homeassistant.const"] = const_module

    sys.modules.pop("custom_components.renogy.const", None)
    sys.modules.pop("custom_components.renogy.device_name", None)
    sys.modules.pop("custom_components.renogy.config_flow", None)
    return importlib.import_module("custom_components.renogy.config_flow")


def test_bluetooth_discovery_uses_fallback_name_for_nameless_device() -> None:
    """Nameless bluetooth matches should use a stable fallback display name."""
    config_flow_module = _load_config_flow_module()
    flow = config_flow_module.RenogyConfigFlow()
    flow.context = {}
    discovery_info = config_flow_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name=None,
        manufacturer_data={0xE14C: b"\x01"},
    )

    form_result = asyncio.run(flow.async_step_bluetooth(discovery_info))

    assert form_result["type"] == "form"
    assert form_result["description_placeholders"]["device_name"] == (
        config_flow_module.UNKNOWN_DEVICE_NAME
    )
    assert flow.context["title_placeholders"] == {
        "name": config_flow_module.UNKNOWN_DEVICE_NAME,
        "address": "AA:BB:CC:DD:EE:FF",
    }


def test_bluetooth_entry_uses_fallback_title_for_nameless_device() -> None:
    """Nameless bluetooth matches should not create entries with None titles."""
    config_flow_module = _load_config_flow_module()
    const_module = importlib.import_module("custom_components.renogy.const")
    flow = config_flow_module.RenogyConfigFlow()
    flow._discovered_device = config_flow_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name=None,
        manufacturer_data={0xE14C: b"\x01"},
    )

    entry_result = asyncio.run(
        flow.async_step_user(
            {
                const_module.CONF_DEVICE_TYPE: const_module.DeviceType.BATTERY.value,
                const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
            }
        )
    )

    assert entry_result == {
        "type": "create_entry",
        "title": config_flow_module.UNKNOWN_DEVICE_NAME,
        "data": {
            const_module.CONF_DEVICE_TYPE: const_module.DeviceType.BATTERY.value,
            const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
            "address": "AA:BB:CC:DD:EE:FF",
        },
    }


def test_manual_entry_detects_battery_when_default_type_is_unchanged() -> None:
    """Manual selection should auto-correct the unchanged controller default."""
    config_flow_module = _load_config_flow_module()
    const_module = importlib.import_module("custom_components.renogy.const")
    flow = config_flow_module.RenogyConfigFlow()
    flow._discovered_devices = {
        "AA:BB:CC:DD:EE:FF": config_flow_module.BluetoothServiceInfoBleak(
            address="AA:BB:CC:DD:EE:FF",
            name=None,
            manufacturer_data={0xE14C: b"\x01"},
        )
    }

    entry_result = asyncio.run(
        flow.async_step_user(
            {
                "address": "AA:BB:CC:DD:EE:FF",
                const_module.CONF_DEVICE_TYPE: const_module.DEFAULT_DEVICE_TYPE,
                const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
            }
        )
    )

    assert entry_result == {
        "type": "create_entry",
        "title": config_flow_module.UNKNOWN_DEVICE_NAME,
        "data": {
            "address": "AA:BB:CC:DD:EE:FF",
            const_module.CONF_DEVICE_TYPE: const_module.DeviceType.BATTERY.value,
            const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
        },
    }


def test_manual_entry_keeps_explicit_device_type_override() -> None:
    """Manual selection should preserve an explicit non-default override."""
    config_flow_module = _load_config_flow_module()
    const_module = importlib.import_module("custom_components.renogy.const")
    flow = config_flow_module.RenogyConfigFlow()
    flow._discovered_devices = {
        "AA:BB:CC:DD:EE:FF": config_flow_module.BluetoothServiceInfoBleak(
            address="AA:BB:CC:DD:EE:FF",
            name=None,
            manufacturer_data={0xE14C: b"\x01"},
        )
    }

    entry_result = asyncio.run(
        flow.async_step_user(
            {
                "address": "AA:BB:CC:DD:EE:FF",
                const_module.CONF_DEVICE_TYPE: const_module.DeviceType.DCC.value,
                const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
            }
        )
    )

    assert entry_result == {
        "type": "create_entry",
        "title": config_flow_module.UNKNOWN_DEVICE_NAME,
        "data": {
            "address": "AA:BB:CC:DD:EE:FF",
            const_module.CONF_DEVICE_TYPE: const_module.DeviceType.DCC.value,
            const_module.CONF_SCAN_INTERVAL: const_module.DEFAULT_SCAN_INTERVAL,
        },
    }
