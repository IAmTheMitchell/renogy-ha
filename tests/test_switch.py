"""Tests for Renogy BLE switch setup."""

from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import MagicMock


def _install_module_stubs() -> None:
    """Install minimal Home Assistant module stubs to import the switch module."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    bluetooth_components_module = cast(
        Any, types.ModuleType("homeassistant.components.bluetooth")
    )
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_components_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class HomeAssistant:
        """Stub HomeAssistant class for testing."""

    def callback(func: Any) -> Any:
        """Return the function unchanged for testing."""
        return func

    core_module.HomeAssistant = HomeAssistant
    core_module.callback = callback
    sys.modules["homeassistant.core"] = core_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    passive_module = cast(
        Any,
        types.ModuleType(
            "homeassistant.components.bluetooth.passive_update_coordinator"
        ),
    )

    class PassiveBluetoothCoordinatorEntity:
        """Stub PassiveBluetoothCoordinatorEntity for testing."""

        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

    passive_module.PassiveBluetoothCoordinatorEntity = PassiveBluetoothCoordinatorEntity
    sys.modules["homeassistant.components.bluetooth.passive_update_coordinator"] = (
        passive_module
    )

    switch_module = cast(Any, types.ModuleType("homeassistant.components.switch"))

    class SwitchEntity:
        """Stub SwitchEntity class for testing."""

    @dataclass
    class SwitchEntityDescription:
        """Stub SwitchEntityDescription for testing."""

        key: str | None = None
        name: str | None = None

    switch_module.SwitchEntity = SwitchEntity
    switch_module.SwitchEntityDescription = SwitchEntityDescription
    sys.modules["homeassistant.components.switch"] = switch_module

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
    sys.modules["homeassistant.const"] = const_module

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyActiveBluetoothCoordinator:
        """Stub coordinator class for testing."""

    class RenogyBLEDevice:
        """Stub BLE device class for testing."""

    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    ble_module.RenogyBLEDevice = RenogyBLEDevice
    sys.modules["custom_components.renogy.ble"] = ble_module


def _load_switch_module():
    """Load the switch module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.switch", None)
    sys.modules.pop("custom_components.renogy", None)

    import importlib

    return importlib.import_module("custom_components.renogy.switch")


def test_switch_setup_skips_non_controller() -> None:
    """Ensure switches are not created for non-controller devices."""
    switch_module = _load_switch_module()
    hass = MagicMock()
    coordinator = MagicMock()
    hass.data = {switch_module.DOMAIN: {"entry-1": {"coordinator": coordinator}}}
    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        switch_module.CONF_DEVICE_TYPE: switch_module.DeviceType.DCC.value
    }
    async_add_entities = MagicMock()

    asyncio.run(switch_module.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_not_called()


def test_switch_setup_adds_controller_switch() -> None:
    """Ensure switches are created for controller devices."""
    switch_module = _load_switch_module()
    device = MagicMock()
    device.name = "BT-TH-12345"
    device.address = "AA:BB:CC:DD:EE:FF"
    device.parsed_data = {}
    device.is_available = True

    coordinator = MagicMock()
    coordinator.device = device
    coordinator.address = device.address
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.async_request_refresh = MagicMock()

    hass = MagicMock()
    hass.data = {switch_module.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        switch_module.CONF_DEVICE_TYPE: switch_module.DeviceType.CONTROLLER.value
    }

    async_add_entities = MagicMock()

    asyncio.run(switch_module.async_setup_entry(hass, config_entry, async_add_entities))

    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], switch_module.RenogyLoadSwitch)
