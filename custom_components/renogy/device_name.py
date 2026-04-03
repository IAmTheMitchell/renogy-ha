"""Helpers for identifying and validating Renogy BLE device names."""

from __future__ import annotations

from .const import (
    DEFAULT_DEVICE_TYPE,
    RENOGY_BATTERY_PRO_PREFIXES,
    RENOGY_BT_PREFIX,
    RENOGY_INVERTER_PREFIX,
    DeviceType,
)

UNKNOWN_DEVICE_NAME_PREFIX = "Unknown"
SHUNT300_BT_PREFIX = "RTMShunt300"
BATTERY_LEGACY_NAME_MARKERS = ("BATT", "BATTERY")
BATTERY_PRO_MANUFACTURER_ID = 0xE14C

DEVICE_NAME_PREFIXES_BY_TYPE: dict[str, tuple[str, ...]] = {
    DeviceType.CONTROLLER.value: (RENOGY_BT_PREFIX,),
    DeviceType.BATTERY.value: (RENOGY_BT_PREFIX, *RENOGY_BATTERY_PRO_PREFIXES),
    DeviceType.INVERTER.value: (RENOGY_INVERTER_PREFIX,),
    DeviceType.DCC.value: (RENOGY_BT_PREFIX,),
    DeviceType.SHUNT300.value: (SHUNT300_BT_PREFIX,),
}

SUPPORTED_BLE_NAME_PREFIXES: tuple[str, ...] = (
    RENOGY_BT_PREFIX,
    RENOGY_INVERTER_PREFIX,
    *RENOGY_BATTERY_PRO_PREFIXES,
    SHUNT300_BT_PREFIX,
)


def has_real_device_name(device_name: str | None) -> bool:
    """Return True when the provided name is usable and not a placeholder."""
    if not isinstance(device_name, str):
        return False
    return bool(device_name) and not device_name.startswith(UNKNOWN_DEVICE_NAME_PREFIX)


def expected_prefixes_for_device_type(device_type: str) -> tuple[str, ...]:
    """Return the expected BLE name prefixes for a device type."""
    return DEVICE_NAME_PREFIXES_BY_TYPE.get(device_type, (RENOGY_BT_PREFIX,))


def is_device_name_ready(device_name: str | None, device_type: str) -> bool:
    """Return True when a name is present and matches the expected prefix."""
    if not isinstance(device_name, str) or not has_real_device_name(device_name):
        return False
    if device_type == DeviceType.BATTERY.value and _is_legacy_battery_name(device_name):
        return True
    return device_name.startswith(expected_prefixes_for_device_type(device_type))


def is_supported_renogy_ble_name(
    device_name: str | None,
    manufacturer_data: dict[int, bytes] | None = None,
) -> bool:
    """Return True for BLE advertisements from supported Renogy devices."""
    return detect_device_type_from_ble_name(
        device_name,
        manufacturer_data=manufacturer_data,
    ) != DEFAULT_DEVICE_TYPE or _is_supported_default_type_name(device_name)


def detect_device_type_from_ble_name(
    device_name: str | None,
    default_device_type: str = DEFAULT_DEVICE_TYPE,
    manufacturer_data: dict[int, bytes] | None = None,
) -> str:
    """Infer the device type from a BLE name, with a provided default fallback."""
    manufacturer_data = manufacturer_data or {}

    if isinstance(device_name, str) and has_real_device_name(device_name):
        if device_name.startswith(RENOGY_INVERTER_PREFIX):
            return DeviceType.INVERTER.value
        if device_name.startswith(RENOGY_BATTERY_PRO_PREFIXES):
            return DeviceType.BATTERY.value
        if _is_legacy_battery_name(device_name):
            return DeviceType.BATTERY.value
        if device_name.startswith(SHUNT300_BT_PREFIX):
            return DeviceType.SHUNT300.value

    if BATTERY_PRO_MANUFACTURER_ID in manufacturer_data:
        return DeviceType.BATTERY.value

    return default_device_type


def _is_legacy_battery_name(device_name: str) -> bool:
    """Return True for legacy battery names and not generic BT-TH devices."""
    if not device_name.startswith(RENOGY_BT_PREFIX):
        return False

    suffix = device_name[len(RENOGY_BT_PREFIX) :].upper()
    return any(marker in suffix for marker in BATTERY_LEGACY_NAME_MARKERS)


def _is_supported_default_type_name(device_name: str | None) -> bool:
    """Return True for supported names that intentionally map to controller/DCC."""
    if not isinstance(device_name, str) or not has_real_device_name(device_name):
        return False

    return any(device_name.startswith(prefix) for prefix in SUPPORTED_BLE_NAME_PREFIXES)
