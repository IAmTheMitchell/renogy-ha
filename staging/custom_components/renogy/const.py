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
RENOGY_INVERTER_PREFIX = "RNGRIU"

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
    SHUNT300 = "shunt300"  # Renogy Shunt300


# List of supported device types
DEVICE_TYPES = [e.value for e in DeviceType]
DEFAULT_DEVICE_TYPE = DeviceType.CONTROLLER.value

# List of fully supported device types
SUPPORTED_DEVICE_TYPES = [
    DeviceType.CONTROLLER.value,
    DeviceType.DCC.value,
    DeviceType.INVERTER.value,
    DeviceType.SHUNT300.value,
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


# Inverter Register Addresses for RIV1220PU (verified against hardware test script)
# Base register: 4000, reading 32 registers
class InverterRegister:
    """Modbus register addresses for RIV1220PU inverter.

    Based on validated test script discover_and_read_renogy_sensors.py
    Reading from register 4000 with these offsets:
    - Index 0-1: AC Input V/I
    - Index 2-4: AC Output V/I/Freq
    - Index 5: Battery Voltage
    - Index 6: Temperature
    """

    # When reading from register 4000:
    # Index 0 = AC Input Voltage (register 4000)
    # Index 1 = AC Input Current (register 4001)
    # Index 2 = AC Output Voltage (register 4002)
    # Index 3 = AC Output Current (register 4003)
    # Index 4 = AC Output Frequency (register 4004)
    # Index 5 = Battery Voltage (register 4005)
    # Index 6 = Temperature (register 4006)

    BATTERY_VOLTAGE = 4005  # Index 5 when reading from 4000
    AC_OUTPUT_VOLTAGE = 4002  # Index 2 when reading from 4000
    AC_OUTPUT_CURRENT = 4003  # Index 3 when reading from 4000
    AC_OUTPUT_FREQUENCY = 4004  # Index 4 when reading from 4000
    TEMPERATURE = 4006  # Index 6 when reading from 4000


# Inverter BLE UUIDs (specific to RNGRIU models)
INVERTER_WRITE_UUID = "0000ffd1-0000-1000-8000-00805f9b34fb"
INVERTER_NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"

# Shunt300 uses the same UUIDs as inverter (standard Renogy BLE)
SHUNT_WRITE_UUID = "0000ffd1-0000-1000-8000-00805f9b34fb"
SHUNT_NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
INVERTER_INIT_UUID = "0000ffd4-0000-1000-8000-00805f9b34fb"

# Inverter device ID (Modbus address)
INVERTER_DEVICE_ID = 32

# Inverter Mode Values
INVERTER_MODES = {
    0: "Off",
    1: "Searching",
    2: "Inverting",
    3: "Error",
    4: "Charging",
    5: "Idle",
}

# Reverse mapping for inverter modes
INVERTER_MODE_VALUES = {v: k for k, v in INVERTER_MODES.items()}
