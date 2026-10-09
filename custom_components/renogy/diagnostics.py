"""Download cached RIV diagnostics without issuing hardware requests."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from renogy_ble import get_inverter_diagnostic_fields

from .const import (
    CONF_DEVICE_TYPE,
    CONF_INVERTER_DIAGNOSTICS,
    CONF_INVERTER_PROFILE,
    CONF_NON_SHUNT_CONNECTION_MODE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    RIV4835CSH1S_INVERTER_PROFILE,
)

_ADDRESS = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
_KEYS = {
    field.key for field in get_inverter_diagnostic_fields(RIV4835CSH1S_INVERTER_PROFILE)
}
_MEASUREMENTS = (
    "model",
    "battery_voltage",
    "battery_percentage",
    "charging_current",
    "charging_power",
    "charging_status",
    "line_charging_current",
    "solar_voltage",
    "solar_current",
    "solar_power",
    "ac_input_voltage",
    "ac_input_current",
    "input_frequency",
    "ac_output_voltage",
    "ac_output_current",
    "ac_output_frequency",
    "load_active_power",
    "load_apparent_power",
    "temperature",
    "inverter_ac_charge_current",
)


def _redact_addresses(value: Any) -> Any:
    """Remove Bluetooth addresses embedded in transport error strings."""
    if isinstance(value, str):
        return _ADDRESS.sub("**REDACTED**", value)
    if isinstance(value, dict):
        return {key: _redact_addresses(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_addresses(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return the last completed snapshot, with identifiers excluded."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id, {}).get("coordinator")
    completed = getattr(coordinator, "data", None)
    data = completed if isinstance(completed, dict) else {}
    option_keys = (
        CONF_DEVICE_TYPE,
        CONF_INVERTER_PROFILE,
        CONF_INVERTER_DIAGNOSTICS,
        CONF_SCAN_INTERVAL,
        CONF_NON_SHUNT_CONNECTION_MODE,
    )
    return _redact_addresses(
        {
            "snapshot_source": "last_completed_poll" if data else "unavailable",
            "configuration": {
                key: entry.options.get(key, entry.data.get(key)) for key in option_keys
            },
            "measurements": {key: data[key] for key in _MEASUREMENTS if key in data},
            "decoded_diagnostics": {key: data[key] for key in _KEYS if key in data},
            "diagnostic_snapshot": data.get("riv_diagnostics", {}),
            "notes": {
                "warning_definitions": "Unverified for this model; raw mask retained.",
                "firmware_components": "Raw words/text; component labels unverified.",
                "timestamps": "Sequential cached reads, not simultaneous measurements.",
            },
        }
    )
