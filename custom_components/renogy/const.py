"""Constants for the Renogy BLE integration."""

import logging
from enum import Enum

DOMAIN = "renogy"

LOGGER = logging.getLogger(__name__)

# BLE scanning constants
DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 10  # seconds
MAX_SCAN_INTERVAL = 600  # seconds

# Availability grace: consecutive failed polls tolerated before the device is
# marked unavailable. Default matches RenogyBLEDevice.max_failures.
DEFAULT_MAX_FAILURES = 3
MIN_MAX_FAILURES = 1
MAX_MAX_FAILURES = 10

# Reconnect cooldown (minutes) before retrying a fully-unavailable device.
# Default matches renogy_ble's UNAVAILABLE_RETRY_INTERVAL.
DEFAULT_UNAVAILABLE_RETRY_INTERVAL = 10  # minutes
MIN_UNAVAILABLE_RETRY_INTERVAL = 1  # minutes
MAX_UNAVAILABLE_RETRY_INTERVAL = 60  # minutes

# Renogy BT-1 and BT-2 module identifiers - devices advertise with these prefixes
RENOGY_BT_PREFIX = "BT-TH-"
RENOGY_INVERTER_PREFIX = "RNGRIU"
RENOGY_REGO_INVERTER_PREFIX = "BTRIC"
RENOGY_BATTERY_PRO_PREFIXES = ("RNGRBP", "RNGC", "RNGPRO")

# Configuration parameters
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MAX_FAILURES = "max_failures"
CONF_UNAVAILABLE_RETRY_INTERVAL = "unavailable_retry_interval"
CONF_DEVICE_TYPE = "device_type"  # New constant for device type
CONF_INVERTER_PROFILE = "inverter_profile"
CONF_INVERTER_DIAGNOSTICS = "inverter_diagnostics"
DEFAULT_INVERTER_DIAGNOSTICS = False
CONF_DEVICE_NAME = "device_name"
CONF_SHUNT_CONNECTION_MODE = "shunt_connection_mode"
CONF_NON_SHUNT_CONNECTION_MODE = "non_shunt_connection_mode"
CONF_COMMUNICATION_HUB_ENABLED = "communication_hub_enabled"
DEFAULT_COMMUNICATION_HUB_ENABLED = False

# Device info
ATTR_MANUFACTURER = "Renogy"


# Define device types as Enum
class DeviceType(Enum):
    CONTROLLER = "controller"
    BATTERY = "battery"
    INVERTER = "inverter"
    DCC = "dcc"  # DC-DC Charger (with or without MPPT)
    SHUNT300 = "shunt300"  # Renogy Shunt300


# List of supported device types
DEVICE_TYPES = [e.value for e in DeviceType]
DEFAULT_DEVICE_TYPE = DeviceType.CONTROLLER.value

GENERIC_INVERTER_PROFILE = "generic"
RIV4835CSH1S_INVERTER_PROFILE = "RIV4835CSH1S"
INVERTER_PROFILES = [GENERIC_INVERTER_PROFILE, RIV4835CSH1S_INVERTER_PROFILE]
DEFAULT_INVERTER_PROFILE = GENERIC_INVERTER_PROFILE


class ShuntConnectionMode(Enum):
    """Supported Smart Shunt connection strategies."""

    SUSTAINED = "sustained"
    INTERMITTENT = "intermittent"


SHUNT_CONNECTION_MODES = [mode.value for mode in ShuntConnectionMode]
DEFAULT_SHUNT_CONNECTION_MODE = ShuntConnectionMode.SUSTAINED.value


class NonShuntConnectionMode(Enum):
    """Supported non-shunt connection strategies."""

    INTERMITTENT = "intermittent"
    PERSISTENT_SESSION = "persistent_session"


NON_SHUNT_CONNECTION_MODES = [mode.value for mode in NonShuntConnectionMode]
DEFAULT_NON_SHUNT_CONNECTION_MODE = NonShuntConnectionMode.INTERMITTENT.value

# List of fully supported device types
SUPPORTED_DEVICE_TYPES = [
    DeviceType.CONTROLLER.value,
    DeviceType.BATTERY.value,
    DeviceType.DCC.value,
    DeviceType.INVERTER.value,
    DeviceType.SHUNT300.value,
]


# Keys that describe the device rather than measure it. They come from the low
# device-info registers (12 and 26 on a controller), which the BT-TH module
# answers unreliably, and renogy-ble clears its parsed data before every poll.
# The coordinator carries these forward from the previous poll when a fresh poll
# did not manage to read them, so a value that never changes does not flip to
# unknown every time one register read times out. Measurements are never
# carried: a stale reading presented as current is worse than an unknown.
STATIC_DEVICE_INFO_KEYS: tuple[str, ...] = ("model", "device_id")
