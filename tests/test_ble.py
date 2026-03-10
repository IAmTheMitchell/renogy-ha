"""Tests for Renogy BLE coordinator error handling."""

import asyncio
import sys
import types
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock


def _install_module_stubs() -> None:
    """Install minimal module stubs to import the BLE coordinator."""
    from tests.mocks import ha_bluetooth, ha_coordinator

    bleak_module = cast(Any, types.ModuleType("bleak"))

    class BleakError(Exception):
        """Stub BleakError for testing."""

    bleak_module.BleakError = BleakError
    sys.modules["bleak"] = bleak_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class CoreState(str, Enum):
        """Stub CoreState enum for testing."""

        running = "running"

    def callback(func):
        """Return the function unchanged for testing."""
        return func

    core_module.CoreState = CoreState
    core_module.HomeAssistant = object
    core_module.callback = callback

    helpers_event_module = cast(Any, types.ModuleType("homeassistant.helpers.event"))
    helpers_event_module.async_track_time_interval = MagicMock()

    bluetooth_module = cast(Any, types.ModuleType("homeassistant.components.bluetooth"))
    bluetooth_module.BluetoothChange = ha_bluetooth.BluetoothChange
    bluetooth_module.BluetoothScanningMode = ha_bluetooth.BluetoothScanningMode
    bluetooth_module.BluetoothServiceInfoBleak = ha_bluetooth.BluetoothServiceInfoBleak
    bluetooth_module.async_get_scanner = MagicMock(return_value=MagicMock())
    bluetooth_module.async_last_service_info = MagicMock()
    bluetooth_module.async_ble_device_from_address = MagicMock()
    bluetooth_module.async_register_callback = MagicMock()

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    components_module.bluetooth = bluetooth_module

    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_module
    sys.modules["homeassistant.components.bluetooth.active_update_coordinator"] = (
        ha_coordinator
    )
    sys.modules["homeassistant.core"] = core_module
    sys.modules["homeassistant.helpers.event"] = helpers_event_module
    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))
    config_entries_module.ConfigEntry = object
    sys.modules["homeassistant.config_entries"] = config_entries_module
    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )
    device_registry_module.async_get = MagicMock()
    sys.modules["homeassistant.helpers"] = helpers_module
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module
    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"

    class Platform(str, Enum):
        """Stub Platform enum for testing."""

        SENSOR = "sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"

    const_module.Platform = Platform
    sys.modules["homeassistant.const"] = const_module

    renogy_ble_module = cast(Any, types.ModuleType("renogy_ble"))
    renogy_ble_ble_module = cast(Any, types.ModuleType("renogy_ble.ble"))
    renogy_ble_shunt_module = cast(Any, types.ModuleType("renogy_ble.shunt"))

    class RenogyBleClient:
        """Stub RenogyBleClient for testing."""

        def __init__(self, scanner):
            self.scanner = scanner

        async def read_device(self, device):
            return MagicMock(success=True, error=None)

    class RenogyBLEDevice:
        """Stub RenogyBLEDevice for testing."""

        def __init__(self, ble_device, advertisement_rssi, device_type=None):
            self.ble_device = ble_device
            self.address = ble_device.address
            self.name = ble_device.name or "Unknown Renogy Device"
            self.rssi = advertisement_rssi
            self.device_type = device_type
            self.parsed_data = {}
            self.update_availability = MagicMock()

    def clean_device_name(name: str) -> str:
        """Return a cleaned device name for testing."""
        return name.strip()

    class RenogyBleReadResult:
        """Stub read result matching the real library interface."""

        def __init__(self, success: bool, parsed_data: dict[str, Any], error=None):
            self.success = success
            self.parsed_data = parsed_data
            self.error = error

    renogy_ble_ble_module.RenogyBleClient = RenogyBleClient
    renogy_ble_ble_module.RenogyBLEDevice = RenogyBLEDevice
    renogy_ble_ble_module.RenogyBleReadResult = RenogyBleReadResult
    renogy_ble_ble_module.clean_device_name = clean_device_name
    renogy_ble_ble_module.LOAD_CONTROL_REGISTER = 0x010A

    class ShuntBleClient:
        """Stub shunt client matching the library interface."""

        async def read_device(self, device):
            return RenogyBleReadResult(True, getattr(device, "parsed_data", {}), None)

    renogy_ble_shunt_module.ShuntBleClient = ShuntBleClient

    sys.modules["renogy_ble"] = renogy_ble_module
    sys.modules["renogy_ble.ble"] = renogy_ble_ble_module
    sys.modules["renogy_ble.shunt"] = renogy_ble_shunt_module


def _load_ble_module():
    """Load the BLE module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.ble", None)
    sys.modules.pop("custom_components.renogy", None)

    import importlib

    return importlib.import_module("custom_components.renogy.ble")


def test_read_device_data_handles_ble_errors():
    """Ensure BLE read exceptions update availability and return False."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
    )

    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-12345",
        rssi=-60,
    )

    coordinator._ble_client.read_device = AsyncMock(
        side_effect=ble_module.BleakError("read failed")
    )

    success = asyncio.run(coordinator._read_device_data(service_info))

    assert success is False
    assert coordinator.last_update_success is False
    coordinator.device.update_availability.assert_called_once()
    call_args = coordinator.device.update_availability.call_args[0]
    assert call_args[0] is False
    assert "read failed" in str(call_args[1])


def test_shunt_device_uses_library_shunt_client():
    """Ensure SHUNT300 devices use the renogy-ble shunt client."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
    )

    assert coordinator._ble_client.__class__.__name__ == "ShuntBleClient"
