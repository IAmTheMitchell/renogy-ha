"""Home Assistant name fallback and entity-readiness policy."""

from __future__ import annotations

from renogy_ble.identification import (
    SHUNT300_BT_PREFIX as SHUNT300_BT_PREFIX,
)
from renogy_ble.identification import (
    detect_device_type_from_model as detect_device_type_from_model,
)
from renogy_ble.identification import (
    identify_advertisement,
    name_matches_device_type,
)
from renogy_ble.identification import (
    is_address_placeholder as is_address_placeholder,
)

from .const import DEFAULT_DEVICE_TYPE

UNKNOWN_DEVICE_NAME_PREFIX = "Unknown"


def has_real_device_name(device_name: str | None, address: str | None = None) -> bool:
    """Reject HA fallback labels and the device's own address (also macOS UUIDs)."""
    return (
        isinstance(device_name, str)
        and bool(device_name)
        and not device_name.startswith(UNKNOWN_DEVICE_NAME_PREFIX)
        and not is_address_placeholder(device_name, address)
    )


def is_device_name_ready(
    device_name: str | None, device_type: str, address: str | None = None
) -> bool:
    """Apply entity readiness policy to library-defined name compatibility."""
    return has_real_device_name(device_name, address) and name_matches_device_type(
        device_name, device_type, address=address
    )


def is_supported_renogy_ble_name(
    device_name: str | None,
    manufacturer_data: dict[int, bytes] | None = None,
    address: str | None = None,
) -> bool:
    """Check library identification after rejecting HA placeholder names."""
    return identify_advertisement(
        device_name if has_real_device_name(device_name, address) else None,
        manufacturer_data=manufacturer_data,
        address=address,
    ).supported


def detect_device_type_from_ble_name(
    device_name: str | None,
    default_device_type: str = DEFAULT_DEVICE_TYPE,
    manufacturer_data: dict[int, bytes] | None = None,
    address: str | None = None,
) -> str:
    """Apply HA's default only when library identification leaves type unresolved."""
    identity = identify_advertisement(
        device_name if has_real_device_name(device_name, address) else None,
        manufacturer_data=manufacturer_data,
        address=address,
    )
    return identity.device_type.value if identity.device_type else default_device_type
