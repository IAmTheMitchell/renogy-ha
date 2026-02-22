"""Helpers for identifying and validating Renogy BLE device names."""

from __future__ import annotations

from .const import DEFAULT_DEVICE_TYPE, RENOGY_BT_PREFIX, DeviceType

UNKNOWN_DEVICE_NAME_PREFIX = "Unknown"
SHUNT300_BT_PREFIX = "RTMShunt300"

DEVICE_NAME_PREFIX_BY_TYPE: dict[str, str] = {
    DeviceType.CONTROLLER.value: RENOGY_BT_PREFIX,
    DeviceType.BATTERY.value: RENOGY_BT_PREFIX,
    DeviceType.INVERTER.value: RENOGY_BT_PREFIX,
    DeviceType.DCC.value: RENOGY_BT_PREFIX,
    DeviceType.SHUNT300.value: SHUNT300_BT_PREFIX,
}

SUPPORTED_BLE_NAME_PREFIXES: tuple[str, ...] = (
    RENOGY_BT_PREFIX,
    SHUNT300_BT_PREFIX,
)


def has_real_device_name(device_name: str | None) -> bool:
    """Return True when the provided name is usable and not a placeholder."""
    if not isinstance(device_name, str):
        return False
    return bool(device_name) and not device_name.startswith(UNKNOWN_DEVICE_NAME_PREFIX)


def expected_prefix_for_device_type(device_type: str) -> str:
    """Return the expected BLE name prefix for a device type."""
    return DEVICE_NAME_PREFIX_BY_TYPE.get(device_type, RENOGY_BT_PREFIX)


def is_device_name_ready(device_name: str | None, device_type: str) -> bool:
    """Return True when a name is present and matches the expected prefix."""
    if not isinstance(device_name, str) or not has_real_device_name(device_name):
        return False
    return device_name.startswith(expected_prefix_for_device_type(device_type))


def is_supported_renogy_ble_name(device_name: str | None) -> bool:
    """Return True for BLE names advertised by supported Renogy devices."""
    if not isinstance(device_name, str) or not has_real_device_name(device_name):
        return False
    return any(device_name.startswith(prefix) for prefix in SUPPORTED_BLE_NAME_PREFIXES)


def detect_device_type_from_ble_name(
    device_name: str | None, default_device_type: str = DEFAULT_DEVICE_TYPE
) -> str:
    """Infer the device type from a BLE name, with a provided default fallback."""
    if not isinstance(device_name, str) or not has_real_device_name(device_name):
        return default_device_type
    if device_name.startswith(SHUNT300_BT_PREFIX):
        return DeviceType.SHUNT300.value
    return default_device_type
