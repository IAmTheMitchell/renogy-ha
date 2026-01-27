"""Test SHUNT300 sensor entity extraction and registration."""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _install_shunt_stubs() -> None:
    """Install minimal stubs so shunt_ble imports without real deps."""
    bleak = types.ModuleType("bleak")
    bleak_exc_mod = types.ModuleType("bleak.exc")
    bleak_error = type("BleakError", (Exception,), {})
    bleak.BleakError = bleak_error
    bleak_exc_mod.BleakError = bleak_error

    bleak_backends = types.ModuleType("bleak.backends")
    bleak_characteristic = types.ModuleType("bleak.backends.characteristic")

    class BleakGATTCharacteristic:
        """Stub characteristic."""

    bleak_characteristic.BleakGATTCharacteristic = BleakGATTCharacteristic
    sys.modules["bleak"] = bleak
    sys.modules["bleak.backends"] = bleak_backends
    sys.modules["bleak.backends.characteristic"] = bleak_characteristic
    sys.modules["bleak.exc"] = bleak_exc_mod

    brc = types.ModuleType("bleak_retry_connector")

    class BleakClientWithServiceCache:  # pragma: no cover - stub
        """Stub client."""

    async def establish_connection(*args, **kwargs):  # pragma: no cover - stub
        return None

    brc.BleakClientWithServiceCache = BleakClientWithServiceCache
    brc.establish_connection = establish_connection
    sys.modules["bleak_retry_connector"] = brc

    renogy_ble = types.ModuleType("renogy_ble")
    renogy_ble_ble = types.ModuleType("renogy_ble.ble")

    class RenogyBLEDevice:  # pragma: no cover - stub
        pass

    class RenogyBleReadResult:  # pragma: no cover - stub
        pass

    def clean_device_name(name: str) -> str:
        return name

    renogy_ble_ble.RenogyBLEDevice = RenogyBLEDevice
    renogy_ble_ble.RenogyBleReadResult = RenogyBleReadResult
    renogy_ble_ble.clean_device_name = clean_device_name
    sys.modules["renogy_ble"] = renogy_ble
    sys.modules["renogy_ble.ble"] = renogy_ble_ble


_install_shunt_stubs()

SHUNT_BLE_PATH = (
    Path(__file__).resolve().parent.parent / "custom_components/renogy/shunt_ble.py"
)
SHUNT_BLE_SPEC = importlib.util.spec_from_file_location(
    "custom_components.renogy.shunt_ble", SHUNT_BLE_PATH
)
shunt_ble = importlib.util.module_from_spec(SHUNT_BLE_SPEC)
assert SHUNT_BLE_SPEC and SHUNT_BLE_SPEC.loader
SHUNT_BLE_SPEC.loader.exec_module(shunt_ble)
parse_shunt_payload = shunt_ble.parse_shunt_payload

# SHUNT300 sensor keys (should match those in sensor.py)
SHUNT_VOLTAGE = "shunt_voltage"
SHUNT_CURRENT = "shunt_current"
SHUNT_POWER = "shunt_power"
SHUNT_SOC = "shunt_soc"
SHUNT_ENERGY = "shunt_energy"


def _build_payload(
    voltage: float = 13.2, current: float = -5.4, starter_voltage: float = 13.1
) -> bytes:
    """Build a fake 110 byte notification payload."""
    payload = bytearray(110)

    # Set main battery voltage at offset 25 (3 bytes, scale 0.001).
    payload[25:28] = int(voltage * 1000).to_bytes(3, "big", signed=False)

    # Set current at offset 21 (3 bytes, signed, scale 0.001).
    payload[21:24] = int(current * 1000).to_bytes(3, "big", signed=True)

    # Set starter battery voltage at offset 30 (2 bytes, scale 0.001).
    payload[30:32] = int(starter_voltage * 1000).to_bytes(2, "big", signed=False)

    # Battery temperature at offset 66 (2 bytes, scale 0.1).
    payload[66:68] = int(24.5 * 10).to_bytes(2, "big", signed=False)

    return bytes(payload)


@pytest.fixture
def mock_shunt300_data():
    """Create mock data for a Shunt300 device."""
    return parse_shunt_payload(_build_payload())


@pytest.fixture
def mock_shunt300_device(mock_shunt300_data):
    device = MagicMock()
    device.name = "RTMShunt30017000123"
    device.address = "4C:E1:74:AA:BB:CC"
    device.is_available = True
    device.device_type = "shunt300"
    device.parsed_data = mock_shunt300_data
    return device


@pytest.fixture
def mock_shunt300_coordinator(mock_shunt300_device, mock_shunt300_data):
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = mock_shunt300_data
    coordinator.device = mock_shunt300_device
    coordinator.address = mock_shunt300_device.address
    return coordinator


def test_shunt_payload_parsing():
    """Validate Smart Shunt payload parsing produces expected keys."""
    data = parse_shunt_payload(_build_payload())

    assert data[SHUNT_VOLTAGE] == 13.2
    assert data[SHUNT_CURRENT] == -5.4
    assert data[SHUNT_POWER] == round(13.2 * -5.4, 2)
    assert SHUNT_SOC in data
    assert SHUNT_ENERGY in data
    assert data["battery_temperature"] == 24.5


def test_shunt300_sensor_values(mock_shunt300_device, mock_shunt300_coordinator):
    """Test that Shunt300 sensor values are extracted correctly."""
    assert mock_shunt300_device.parsed_data[SHUNT_VOLTAGE] == 13.2
    assert mock_shunt300_coordinator.data[SHUNT_CURRENT] == -5.4
    assert mock_shunt300_coordinator.data[SHUNT_POWER] == round(13.2 * -5.4, 2)
