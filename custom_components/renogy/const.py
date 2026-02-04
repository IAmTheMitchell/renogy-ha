"""Constants for the Renogy BLE integration."""

import logging
from enum import Enum

DOMAIN = "renogy"

LOGGER = logging.getLogger(__name__)

# BLE scanning constants
DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 10  # seconds
MAX_SCAN_INTERVAL = 600  # seconds

# Renogy BT-1 and BT-2 module identifiers - devices advertise with these prefixes
RENOGY_BT_PREFIX = "BT-TH-"

# Configuration parameters
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEVICE_TYPE = "device_type"  # New constant for device type

# Device info
ATTR_MANUFACTURER = "Renogy"


# Define device types as Enum
class DeviceType(Enum):
    CONTROLLER = "controller"
    BATTERY = "battery"
    INVERTER = "inverter"
    DCC = "dcc"  # DC-DC Charger (with or without MPPT)
    SHUNT = "shunt"  # Renogy Smart SHUNT


# List of supported device types
DEVICE_TYPES = [e.value for e in DeviceType]
DEFAULT_DEVICE_TYPE = DeviceType.CONTROLLER.value

# List of fully supported device types
SUPPORTED_DEVICE_TYPES = [
    DeviceType.CONTROLLER.value,
    DeviceType.DCC.value,
    DeviceType.SHUNT.value,  # SHUNT now fully supported
]


# DCC Charger Register Addresses (for write operations)
class DCCRegister:
    """Modbus register addresses for DCC charger parameters."""

    MAX_CHARGING_CURRENT = 0xE001
    BATTERY_TYPE = 0xE004
    OVERVOLTAGE_THRESHOLD = 0xE005
    CHARGING_LIMIT_VOLTAGE = 0xE006
    EQUALIZATION_VOLTAGE = 0xE007
    BOOST_VOLTAGE = 0xE008
    FLOAT_VOLTAGE = 0xE009
    BOOST_RETURN_VOLTAGE = 0xE00A
    OVERDISCHARGE_RETURN_VOLTAGE = 0xE00B
    UNDERVOLTAGE_WARNING = 0xE00C
    OVERDISCHARGE_VOLTAGE = 0xE00D
    DISCHARGE_LIMIT_VOLTAGE = 0xE00E
    OVERDISCHARGE_DELAY = 0xE010
    EQUALIZATION_TIME = 0xE011
    BOOST_TIME = 0xE012
    EQUALIZATION_INTERVAL = 0xE013
    TEMPERATURE_COMPENSATION = 0xE014
    REVERSE_CHARGING_VOLTAGE = 0xE020
    SOLAR_CUTOFF_CURRENT = 0xE038


# DCC Battery Type Values
DCC_BATTERY_TYPES = {
    0: "custom",
    1: "open",
    2: "sealed",
    3: "gel",
    4: "lithium",
}

# Reverse mapping for setting battery type
DCC_BATTERY_TYPE_VALUES = {v: k for k, v in DCC_BATTERY_TYPES.items()}

# DCC Max Charging Current options (in amps)
# Device stores as centiamps, so 40A = 4000
DCC_MAX_CURRENT_OPTIONS = [10, 20, 30, 40, 50, 60]

# Mapping from amps to centiamps for writing
DCC_MAX_CURRENT_TO_DEVICE = {amp: amp * 100 for amp in DCC_MAX_CURRENT_OPTIONS}
