"""Tests for Renogy BLE coordinator error handling."""

import asyncio
import sys
import types
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch


def _install_module_stubs() -> None:
    """Install minimal module stubs to import the BLE coordinator."""
    from tests.mocks import ha_bluetooth, ha_coordinator

    bleak_module = cast(Any, types.ModuleType("bleak"))

    class BleakError(Exception):
        """Stub BleakError for testing."""

    class BleakClient:
        """Stub BleakClient for sustained shunt tests."""

        def set_disconnected_callback(self, _callback) -> None:
            """Store disconnect callback."""

        async def start_notify(self, *_args, **_kwargs) -> None:
            """Start notifications."""

        async def stop_notify(self, *_args, **_kwargs) -> None:
            """Stop notifications."""

        async def disconnect(self) -> None:
            """Disconnect the client."""

    bleak_module.BleakError = BleakError
    bleak_module.BleakClient = BleakClient
    sys.modules["bleak"] = bleak_module
    bleak_characteristic_module = cast(
        Any, types.ModuleType("bleak.backends.characteristic")
    )
    bleak_characteristic_module.BleakGATTCharacteristic = object
    sys.modules["bleak.backends.characteristic"] = bleak_characteristic_module
    retry_connector_module = cast(Any, types.ModuleType("bleak_retry_connector"))
    retry_connector_module.clear_cache = AsyncMock(return_value=False)
    retry_connector_module.establish_connection = AsyncMock(return_value=BleakClient())
    sys.modules["bleak_retry_connector"] = retry_connector_module

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
    bluetooth_module.async_scanner_count = MagicMock(return_value=1)
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
    const_module.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"

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

        def __init__(self, scanner, transport_mode="per_operation"):
            self.scanner = scanner
            self.transport_mode = transport_mode
            self.close = AsyncMock()

        async def read_device(self, device):
            return MagicMock(success=True, error=None)

    class RenogyBLEDevice:
        """Stub RenogyBLEDevice for testing."""

        def __init__(
            self,
            ble_device,
            advertisement_rssi,
            device_type=None,
            manufacturer_data=None,
        ):
            self.ble_device = ble_device
            self.address = ble_device.address
            self.name = ble_device.name or "Unknown Renogy Device"
            self.rssi = advertisement_rssi
            self.device_type = device_type
            self.manufacturer_data = manufacturer_data or {}
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

        def _integrate_energy_totals(
            self, *, device_address: str, power_w: float | None, now_ts: float
        ) -> tuple[float, float]:
            """Return deterministic energy totals for testing."""
            return (0.0, 0.0)

        async def read_device(self, device):
            return RenogyBleReadResult(True, getattr(device, "parsed_data", {}), None)

    renogy_ble_shunt_module.ShuntBleClient = ShuntBleClient
    renogy_ble_shunt_module.SHUNT_EXPECTED_PAYLOAD_LENGTH = 110
    renogy_ble_shunt_module.SHUNT_NOTIFY_CHAR_UUID = (
        "0000c411-0000-1000-8000-00805f9b34fb"
    )
    renogy_ble_shunt_module._find_valid_payload_window = MagicMock(return_value=None)

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


def test_sustained_shunt_device_defaults_to_generic_client():
    """Ensure sustained SHUNT300 mode avoids the library shunt read client."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )

    assert coordinator._ble_client.__class__.__name__ == "RenogyBleClient"


def test_update_device_detects_battery_from_manufacturer_data_only():
    """Battery manufacturer data should override missing battery name prefixes."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-123456",
        rssi=-60,
    )
    service_info.advertisement.manufacturer_data = {0xE14C: b"\x01"}

    device = coordinator._update_device_from_service_info(service_info)

    assert coordinator.device_type == "battery"
    assert device.device_type == "battery"
    assert device.manufacturer_data == {0xE14C: b"\x01"}


def test_update_device_preserves_cached_manufacturer_data() -> None:
    """Later advertisements should not erase cached manufacturer data."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
    )
    initial_service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name=None,
        rssi=-60,
    )
    initial_service_info.advertisement.manufacturer_data = {0xE14C: b"\x01"}
    coordinator._update_device_from_service_info(initial_service_info)

    later_service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name=None,
        rssi=-55,
    )
    later_service_info.advertisement.manufacturer_data = {}

    device = coordinator._update_device_from_service_info(later_service_info)

    assert coordinator.device_type == "battery"
    assert device.device_type == "battery"
    assert device.manufacturer_data == {0xE14C: b"\x01"}


def test_intermittent_shunt_device_uses_library_shunt_client():
    """Ensure intermittent SHUNT300 mode keeps using the library shunt client."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="intermittent",
    )

    assert coordinator._ble_client.__class__.__name__ == "ShuntBleClient"


def test_non_shunt_device_defaults_to_intermittent_client():
    """Ensure non-shunt devices default to reconnect-per-refresh transport."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
    )

    assert coordinator._ble_client.__class__.__name__ == "RenogyBleClient"
    assert coordinator._ble_client.transport_mode == "per_operation"


def test_non_shunt_persistent_mode_uses_library_persistent_transport():
    """Ensure non-shunt persistent mode opts into the library session transport."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )

    assert coordinator._ble_client.__class__.__name__ == "RenogyBleClient"
    assert coordinator._ble_client.transport_mode == "persistent_session"


def test_non_shunt_persistent_mode_does_not_rebuild_client_on_update():
    """Ensure persistent non-shunt updates keep the same library client instance."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )
    original_client = coordinator._ble_client
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-12345",
        rssi=-60,
    )

    coordinator._update_device_from_service_info(service_info)
    coordinator._update_device_from_service_info(service_info)

    assert coordinator._ble_client is original_client


def test_async_shutdown_closes_persistent_library_client():
    """Ensure coordinator shutdown releases any persistent library session."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )

    asyncio.run(coordinator.async_shutdown())

    coordinator._ble_client.close.assert_awaited_once()


def test_persistent_refresh_uses_cached_device_when_service_info_expires():
    """Ensure persistent sessions still poll after HA drops advertisement cache."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-12345",
        rssi=-60,
    )
    coordinator._update_device_from_service_info(service_info)
    coordinator._async_poll_device = AsyncMock(return_value={})
    ble_module.bluetooth.async_last_service_info.return_value = None

    asyncio.run(coordinator.async_request_refresh())

    coordinator._async_poll_device.assert_awaited_once_with(None)
    logger.error.assert_not_called()


def test_refresh_without_service_info_still_fails_without_cached_device():
    """Ensure missing service info still fails without persistent cached context."""
    ble_module = _load_ble_module()
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
    )
    ble_module.bluetooth.async_last_service_info.return_value = None

    asyncio.run(coordinator.async_request_refresh())

    assert coordinator.last_update_success is False
    logger.error.assert_called_once()


def test_read_device_data_uses_cached_device_without_service_info():
    """Ensure reads can reuse the cached BLE device for persistent sessions."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-12345",
        rssi=-60,
    )
    coordinator._update_device_from_service_info(service_info)
    coordinator._ble_client.read_device = AsyncMock(
        return_value=MagicMock(success=True, error=None)
    )
    coordinator.device.parsed_data = {"battery_voltage": 14.4}

    success = asyncio.run(coordinator._read_device_data(None))

    assert success is True
    coordinator._ble_client.read_device.assert_awaited_once_with(coordinator.device)
    assert coordinator.data == {"battery_voltage": 14.4}


def test_persistent_load_write_uses_cached_device_when_service_info_expires():
    """Ensure load writes can reuse persistent cached device context."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="controller",
        non_shunt_connection_mode="persistent_session",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="BT-TH-12345",
        rssi=-60,
    )
    coordinator._update_device_from_service_info(service_info)
    coordinator._ble_client.write_single_register = AsyncMock(
        return_value=MagicMock(success=True, error=None)
    )
    ble_module.bluetooth.async_last_service_info.return_value = None

    success = asyncio.run(coordinator.async_set_load_state(True))

    assert success is True
    coordinator._ble_client.write_single_register.assert_awaited_once_with(
        coordinator.device,
        0x010A,
        1,
    )


def test_sustained_shunt_refresh_does_not_poll():
    """Ensure sustained SHUNT300 refresh requests do not open a competing read."""
    ble_module = _load_ble_module()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    coordinator._async_poll_device = AsyncMock()

    asyncio.run(coordinator.async_request_refresh())

    coordinator._async_poll_device.assert_not_awaited()


def test_sustained_shunt_notification_ignores_duplicate_payloads():
    """Ensure identical sustained shunt payloads do not spam listeners."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.loop.call_soon_threadsafe = lambda callback: callback()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    coordinator.device = MagicMock(parsed_data={})
    listener = MagicMock()
    coordinator.async_add_listener(listener)

    payload = (
        b"\x01\x02",
        {
            "shunt_voltage": 13.2,
            "shunt_current": 1.5,
            "shunt_power": 19.8,
            "shunt_soc": 85.0,
        },
    )
    ble_module.shunt_find_valid_payload_window = MagicMock(return_value=payload)

    with patch.object(ble_module.time, "monotonic", side_effect=[100.0, 110.0]):
        coordinator._process_sustained_shunt_notification(b"first")
        coordinator._process_sustained_shunt_notification(b"second")

    assert coordinator.data["shunt_voltage"] == 13.2
    assert listener.call_count == 1


def test_sustained_shunt_notification_populates_raw_words():
    """Ensure sustained shunt updates expose raw_words for diagnostics."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.loop.call_soon_threadsafe = lambda callback: callback()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    coordinator.device = MagicMock(parsed_data={})

    payload = (
        b"\x12\x34\xab\xcd",
        {
            "shunt_voltage": 13.2,
            "shunt_current": 1.5,
            "shunt_power": 19.8,
            "shunt_soc": 85.0,
        },
    )
    ble_module.shunt_find_valid_payload_window = MagicMock(return_value=payload)

    with patch.object(ble_module.time, "monotonic", return_value=100.0):
        assert coordinator._process_sustained_shunt_notification(b"payload") is True

    assert coordinator.data["raw_payload"] == "1234abcd"
    assert coordinator.data["raw_words"] == [0x1234, 0xABCD]
    assert coordinator.device.parsed_data["raw_words"] == [0x1234, 0xABCD]


def test_sustained_shunt_notification_recovers_from_duplicate_payload_after_error():
    """Ensure duplicate payloads still restore availability after listener errors."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.loop.call_soon_threadsafe = lambda callback: callback()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    coordinator.device = MagicMock(parsed_data={})
    listener = MagicMock()
    coordinator.async_add_listener(listener)

    payload = (
        b"\x01\x02",
        {
            "shunt_voltage": 13.2,
            "shunt_current": 1.5,
            "shunt_power": 19.8,
            "shunt_soc": 85.0,
        },
    )
    ble_module.shunt_find_valid_payload_window = MagicMock(return_value=payload)

    with patch.object(ble_module.time, "monotonic", side_effect=[100.0, 110.0]):
        coordinator._process_sustained_shunt_notification(b"first")
        coordinator.last_update_success = False
        coordinator._process_sustained_shunt_notification(b"second")

    assert coordinator.last_update_success is True
    assert listener.call_count == 2
    assert coordinator.device.update_availability.call_args_list[-1][0] == (True, None)


def test_sustained_shunt_listener_cancellation_skips_disconnect():
    """Ensure listener cancellation schedules disconnect cleanup on shutdown."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = ble_module.CoreState.running
    logger = MagicMock()
    disconnect_tasks = []

    def _create_background_task(coro, *, name=None):
        del name
        task = asyncio.create_task(coro)
        disconnect_tasks.append(task)
        return task

    hass.async_create_background_task = _create_background_task
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    ble_module.bluetooth.async_last_service_info.return_value = service_info
    client = MagicMock()
    client.is_connected = True
    client.start_notify = AsyncMock()
    client.disconnect = AsyncMock(
        side_effect=AssertionError("disconnect should not be awaited")
    )
    ble_module.establish_connection = AsyncMock(return_value=client)
    original_sleep = ble_module.asyncio.sleep
    ble_module.asyncio.sleep = AsyncMock(side_effect=asyncio.CancelledError())

    try:
        asyncio.run(coordinator._shunt_notification_loop())
    finally:
        ble_module.asyncio.sleep = original_sleep

    assert len(disconnect_tasks) == 1
    client.disconnect.assert_awaited_once()


def test_sustained_shunt_notification_handler_logs_and_recovers():
    """Ensure callback exceptions are logged instead of escaping the notify handler."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = ble_module.CoreState.running
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    ble_module.bluetooth.async_last_service_info.return_value = service_info
    coordinator._process_sustained_shunt_notification = MagicMock(
        side_effect=RuntimeError("bad packet")
    )
    client = MagicMock()
    client.is_connected = False

    async def _start_notify(_uuid, callback) -> None:
        callback("sender", bytearray(b"packet"))

    client.start_notify = AsyncMock(side_effect=_start_notify)
    client.disconnect = AsyncMock()
    ble_module.establish_connection = AsyncMock(return_value=client)
    original_sleep = ble_module.asyncio.sleep
    ble_module.asyncio.sleep = AsyncMock(side_effect=asyncio.CancelledError())

    try:
        try:
            asyncio.run(coordinator._shunt_notification_loop())
        except asyncio.CancelledError:
            pass
    finally:
        ble_module.asyncio.sleep = original_sleep

    logger.warning.assert_called_once()
    client.disconnect.assert_not_awaited()


def test_sustained_shunt_listener_error_notifies_entities():
    """Ensure sustained listener errors notify listeners about availability changes."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = ble_module.CoreState.running
    hass.loop.call_soon_threadsafe = lambda callback: callback()
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    listener = MagicMock()
    coordinator.async_add_listener(listener)
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    ble_module.bluetooth.async_last_service_info.return_value = service_info
    client = MagicMock()
    client.start_notify = AsyncMock(side_effect=RuntimeError("notify failed"))
    client.stop_notify = AsyncMock()
    client.disconnect = AsyncMock()
    ble_module.establish_connection = AsyncMock(return_value=client)
    original_sleep = ble_module.asyncio.sleep
    ble_module.asyncio.sleep = AsyncMock(side_effect=asyncio.CancelledError())

    try:
        try:
            asyncio.run(coordinator._shunt_notification_loop())
        except asyncio.CancelledError:
            pass
    finally:
        ble_module.asyncio.sleep = original_sleep

    assert coordinator.last_update_success is False
    coordinator.device.update_availability.assert_called_with(
        False, client.start_notify.side_effect
    )
    assert listener.call_count == 1
    assert client.disconnect.await_count == 1


def test_sustained_shunt_listener_waits_for_started_scanner_and_fresh_advertisement():
    """Ensure the first sustained shunt connect waits for startup readiness."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = "starting"
    started_callbacks = []

    def _listen_once(_event, callback):
        started_callbacks.append(callback)

        def _unsub() -> None:
            return None

        return _unsub

    hass.bus.async_listen_once = _listen_once
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    stale_service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    stale_service_info.time = 90.0
    fresh_service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    fresh_service_info.time = 105.0
    ble_module.bluetooth.async_last_service_info.return_value = stale_service_info
    ble_module.bluetooth.async_scanner_count.return_value = 0

    async def _run_wait() -> None:
        with patch.object(ble_module.time, "monotonic", return_value=100.0):
            wait_task = asyncio.create_task(
                coordinator._async_wait_for_shunt_startup_ready()
            )
            await asyncio.sleep(0)
            assert not wait_task.done()

            hass.state = ble_module.CoreState.running
            started_callbacks[0](None)
            await asyncio.sleep(0)
            assert not wait_task.done()

            ble_module.bluetooth.async_scanner_count.return_value = 1
            bluetooth_callback = ble_module.bluetooth.async_register_callback.call_args[
                0
            ][1]
            bluetooth_callback(
                fresh_service_info,
                ble_module.BluetoothChange.ADVERTISEMENT,
            )
            await wait_task

    asyncio.run(_run_wait())

    assert coordinator._shunt_startup_gate_complete is True


def test_sustained_shunt_listener_clears_bluez_state_before_reconnect():
    """Ensure sustained shunt reconnect uses a rediscovered device after cache clear."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = ble_module.CoreState.running
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    ble_module.bluetooth.async_last_service_info.return_value = service_info
    refreshed_device = MagicMock()
    refreshed_device.address = service_info.address
    refreshed_device.name = service_info.name
    ble_module.bluetooth.async_ble_device_from_address.return_value = refreshed_device
    client = MagicMock()
    client.is_connected = False
    client.start_notify = AsyncMock()
    client.disconnect = AsyncMock()

    call_order: list[str] = []

    async def _clear_cache(_address: str) -> bool:
        call_order.append("clear_cache")
        return True

    async def _establish_connection(*_args, **_kwargs):
        call_order.append("establish_connection")
        assert _args[1] is refreshed_device
        return client

    ble_module.clear_cache = AsyncMock(side_effect=_clear_cache)
    ble_module.establish_connection = AsyncMock(side_effect=_establish_connection)
    original_sleep = ble_module.asyncio.sleep
    ble_module.asyncio.sleep = AsyncMock(side_effect=asyncio.CancelledError())

    try:
        try:
            asyncio.run(coordinator._shunt_notification_loop())
        except asyncio.CancelledError:
            pass
    finally:
        ble_module.asyncio.sleep = original_sleep

    assert call_order[:2] == ["clear_cache", "establish_connection"]
    ble_module.clear_cache.assert_awaited_once_with("AA:BB:CC:DD:EE:FF")
    ble_module.bluetooth.async_ble_device_from_address.assert_called_once_with(
        hass, "AA:BB:CC:DD:EE:FF", connectable=True
    )
    assert coordinator.device.ble_device is refreshed_device


def test_sustained_shunt_listener_waits_for_rediscovery_after_cache_clear():
    """Ensure sustained shunt reconnect waits for a rediscovered device handle."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    hass.state = ble_module.CoreState.running
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="sustained",
    )
    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )
    ble_module.bluetooth.async_last_service_info.return_value = service_info
    ble_module.bluetooth.async_ble_device_from_address.return_value = None
    ble_module.clear_cache = AsyncMock(return_value=True)
    ble_module.establish_connection = AsyncMock()
    original_sleep = ble_module.asyncio.sleep
    ble_module.asyncio.sleep = AsyncMock(side_effect=asyncio.CancelledError())

    try:
        try:
            asyncio.run(coordinator._shunt_notification_loop())
        except asyncio.CancelledError:
            pass
    finally:
        ble_module.asyncio.sleep = original_sleep

    ble_module.clear_cache.assert_awaited_once_with("AA:BB:CC:DD:EE:FF")
    ble_module.establish_connection.assert_not_awaited()


def test_shunt_poll_keeps_last_good_data_when_library_read_fails():
    """Ensure HA preserves the last good shunt snapshot on library read failure."""
    ble_module = _load_ble_module()
    hass = MagicMock()
    logger = MagicMock()
    coordinator = ble_module.RenogyActiveBluetoothCoordinator(
        hass=hass,
        logger=logger,
        address="AA:BB:CC:DD:EE:FF",
        scan_interval=30,
        device_type="shunt300",
        shunt_connection_mode="intermittent",
    )
    cached_data = {"shunt_voltage": 13.2, "reading_verified": True}
    failed_read_data = {"shunt_voltage": 15.7, "reading_verified": False}
    coordinator.data = dict(cached_data)

    service_info = ble_module.BluetoothServiceInfoBleak(
        address="AA:BB:CC:DD:EE:FF",
        name="RTMShunt300A1B2",
        rssi=-60,
    )

    coordinator._ble_client.read_device = AsyncMock(
        return_value=MagicMock(
            success=False,
            parsed_data=failed_read_data,
            error=RuntimeError("history-only payload"),
        )
    )

    result = asyncio.run(coordinator._async_poll_device(service_info))

    assert result == cached_data
    assert coordinator.data == cached_data
    assert coordinator.last_update_success is False
    coordinator.device.update_availability.assert_called_once()
    call_args = coordinator.device.update_availability.call_args[0]
    assert call_args[0] is False
    assert "history-only payload" in str(call_args[1])
