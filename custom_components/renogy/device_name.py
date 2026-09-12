"""Helpers for identifying and validating Renogy BLE device names."""

from __future__ import annotations

import re

from .const import (
    DEFAULT_DEVICE_TYPE,
    RENOGY_BATTERY_PRO_PREFIXES,
    RENOGY_BT_PREFIX,
    RENOGY_INVERTER_PREFIX,
    RENOGY_REGO_INVERTER_PREFIX,
    DeviceType,
)

UNKNOWN_DEVICE_NAME_PREFIX = "Unknown"

# DC-DC charger model families: DCC30S/DCC50S and their successors
# RBC20D1U/RBC30D1S/RBC50D1S(-G6) etc. The "D" after the amperage marks
# the DC input variant (AC chargers use a different letter).
DCC_MODEL_PATTERN = re.compile(r"^(DCC|RBC\d+D)", re.IGNORECASE)
SHUNT300_BT_PREFIX = "RTMShunt300"
BATTERY_LEGACY_NAME_MARKERS = ("BATT", "BATTERY")
BATTERY_PRO_MANUFACTURER_ID = 0xE14C

DEVICE_NAME_PREFIXES_BY_TYPE: dict[str, tuple[str, ...]] = {
    DeviceType.CONTROLLER.value: (RENOGY_BT_PREFIX,),
    DeviceType.BATTERY.value: (RENOGY_BT_PREFIX, *RENOGY_BATTERY_PRO_PREFIXES),
    DeviceType.INVERTER.value: (RENOGY_INVERTER_PREFIX, RENOGY_REGO_INVERTER_PREFIX),
    DeviceType.DCC.value: (RENOGY_BT_PREFIX,),
    DeviceType.SHUNT300.value: (SHUNT300_BT_PREFIX,),
}

SUPPORTED_BLE_NAME_PREFIXES: tuple[str, ...] = (
    RENOGY_BT_PREFIX,
    RENOGY_INVERTER_PREFIX,
    RENOGY_REGO_INVERTER_PREFIX,
    *RENOGY_BATTERY_PRO_PREFIXES,
    SHUNT300_BT_PREFIX,
)


def has_real_device_name(device_name: str | None, address: str | None = None) -> bool:
    """Return True when the provided name is usable and not a placeholder.

    Pass ``address`` whenever the caller has it. Without it the
    address-placeholder check below cannot run, because deciding whether a name
    is really an address requires the address to compare against. Every call
    site in this integration passes one.
    """
    if not isinstance(device_name, str):
        return False
    if not device_name or device_name.startswith(UNKNOWN_DEVICE_NAME_PREFIX):
        return False
    return not is_address_placeholder(device_name, address)


def is_address_placeholder(device_name: str | None, address: str | None) -> bool:
    """Return True when the "name" is really the device's own address.

    A Renogy device only sends its local name in the scan response, so under
    passive scanning -- which is what Home Assistant's default ``auto`` mode
    picks on any adapter that supports it -- no advertisement ever carries one.
    The stack below us then falls back to the address, and that string is what
    reaches this integration as a name. Treating it as a real name is worse
    than having none: it overwrites a good cached name, and battery variant
    detection keys on the ``RNGPRO``/``RBT`` prefix, so it fails with the
    confusing "Unable to determine Renogy battery variant for
    14:9C:EF:03:68:81".

    Recognise it the way the layers below already do -- by comparing against
    the address, never by matching a pattern. Two fallbacks exist, one per
    layer:

    * ``habluetooth`` builds the service info name as ``local_name or
      device.name or device.address`` and undoes it by testing
      ``name == address`` (``habluetooth/models.py``, 6.8.0). That is the
      fallback this integration actually sees.
    * BlueZ generates an ``Alias`` of the address with ``:`` replaced by ``-``.
      ``bleak`` normalises that one to ``None`` before it reaches us
      (``bleak/backends/bluezdbus/scanner.py``, 3.0.2), so it should not get
      this far -- it is checked anyway because the cost is one comparison.

    A pattern cannot do this job: ``BLEDevice.address`` is a **UUID on macOS**,
    not a BD address, so no MAC-shaped regex would recognise the placeholder
    there. Comparing against the address is correct on every platform.
    """
    if not isinstance(device_name, str) or not address:
        return False
    name = device_name.strip().casefold()
    resolved = address.strip().casefold()
    return name == resolved or name == resolved.replace(":", "-")


def expected_prefixes_for_device_type(device_type: str) -> tuple[str, ...]:
    """Return the expected BLE name prefixes for a device type."""
    return DEVICE_NAME_PREFIXES_BY_TYPE.get(device_type, (RENOGY_BT_PREFIX,))


def is_device_name_ready(
    device_name: str | None, device_type: str, address: str | None = None
) -> bool:
    """Return True when a name is present and matches the expected prefix."""
    if not isinstance(device_name, str) or not has_real_device_name(
        device_name, address
    ):
        return False
    if device_type == DeviceType.BATTERY.value and _is_legacy_battery_name(device_name):
        return True
    return device_name.startswith(expected_prefixes_for_device_type(device_type))


def is_supported_renogy_ble_name(
    device_name: str | None,
    manufacturer_data: dict[int, bytes] | None = None,
    address: str | None = None,
) -> bool:
    """Return True for BLE advertisements from supported Renogy devices."""
    return detect_device_type_from_ble_name(
        device_name,
        manufacturer_data=manufacturer_data,
        address=address,
    ) != DEFAULT_DEVICE_TYPE or _is_supported_default_type_name(device_name, address)


def detect_device_type_from_ble_name(
    device_name: str | None,
    default_device_type: str = DEFAULT_DEVICE_TYPE,
    manufacturer_data: dict[int, bytes] | None = None,
    address: str | None = None,
) -> str:
    """Infer the device type from a BLE name, with a provided default fallback."""
    manufacturer_data = manufacturer_data or {}

    if isinstance(device_name, str) and has_real_device_name(device_name, address):
        if device_name.startswith(
            (RENOGY_INVERTER_PREFIX, RENOGY_REGO_INVERTER_PREFIX)
        ):
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


def detect_device_type_from_model(model: str | None) -> str | None:
    """Infer the device type from a device-reported model string.

    BLE names cannot distinguish a BT-TH module on a solar controller from
    one on a DC-DC charger, but the model register can. Returns None when
    the model does not identify a specific device type.
    """
    if not isinstance(model, str):
        return None

    normalized = model.strip()
    if not normalized:
        return None

    if DCC_MODEL_PATTERN.match(normalized):
        return DeviceType.DCC.value

    return None


def _is_legacy_battery_name(device_name: str) -> bool:
    """Return True for legacy battery names and not generic BT-TH devices."""
    if not device_name.startswith(RENOGY_BT_PREFIX):
        return False

    suffix = device_name[len(RENOGY_BT_PREFIX) :].upper()
    return any(marker in suffix for marker in BATTERY_LEGACY_NAME_MARKERS)


def _is_supported_default_type_name(
    device_name: str | None, address: str | None = None
) -> bool:
    """Return True for supported names that intentionally map to controller/DCC."""
    if not isinstance(device_name, str) or not has_real_device_name(
        device_name, address
    ):
        return False

    return any(device_name.startswith(prefix) for prefix in SUPPORTED_BLE_NAME_PREFIXES)
