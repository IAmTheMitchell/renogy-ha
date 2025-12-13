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


# List of supported device types
DEVICE_TYPES = [e.value for e in DeviceType]
DEFAULT_DEVICE_TYPE = DeviceType.CONTROLLER.value

# List of fully supported device types (currently only controller)
SUPPORTED_DEVICE_TYPES = [DeviceType.CONTROLLER.value]

# BLE Characteristics and Service UUIDs
RENOGY_READ_CHAR_UUID = (
    "0000fff1-0000-1000-8000-00805f9b34fb"  # Characteristic for reading data
)
RENOGY_WRITE_CHAR_UUID = (
    "0000ffd1-0000-1000-8000-00805f9b34fb"  # Characteristic for writing commands
)

# Time in minutes to wait before attempting to reconnect to unavailable devices
UNAVAILABLE_RETRY_INTERVAL = 10

# Maximum time to wait for a notification response (seconds)
MAX_NOTIFICATION_WAIT_TIME = 2.0

# Default device ID for Renogy devices
DEFAULT_DEVICE_ID = 0xFF

# Modbus commands for requesting data
COMMANDS = {
    DeviceType.CONTROLLER.value: {
        "device_info": (3, 12, 8),
        "device_id": (3, 26, 1),
        "battery": (3, 57348, 1),
        "pv": (3, 256, 34),
    },
}


# Sensor validation limits

# Format: sensor_key: (min_value, max_value, max_change_per_update)

# max_change_per_update helps detect invalid spikes in data

SENSOR_VALIDATION_LIMITS = {

    # Battery sensors

    "battery_voltage": (0, 80, 5),  # 0-80V, max change 5V

    "battery_current": (-100, 100, 50),  # -100 to 100A, max change 50A

    "battery_percentage": (0, 100, 90),  # 0-100%, no max change limit

    "battery_temperature": (-40, 85, 3),  # -40 to 85°C, max change 20°C

    "charging_amp_hours_today": (0, 10000, 300),  # 0-10000Ah, no max change (cumulative)

    "discharging_amp_hours_today": (0, 10000, 30),  # 0-10000Ah, no max change (cumulative)

    

    # PV (solar panel) sensors

    "pv_voltage": (0, 150, 10),  # 0-150V, max change 10V

    "pv_current": (0, 100, 50),  # 0-100A, max change 50A

    "pv_power": (0, 600, 600),  # 0-5000W, max change 2000W

    "max_charging_power_today": (0, 5000, 800),  # 0-5000W, no max change (max value)

    "power_generation_today": (0, 50000, 10000),  # 0-50000Wh, no max change (cumulative)

    "power_generation_total": (0, 10000, 30),  # 0-1000000kWh, no max change (cumulative)

    

    # Load sensors

    "load_voltage": (0, 80, 20),  # 0-80V, max change 5V

    "load_current": (0, 100, 50),  # 0-100A, max change 50A

    "load_power": (0, 3000, 1500),  # 0-3000W, max change 1500W

    "power_consumption_today": (0, 50000, 1000),  # 0-50000Wh, no max change (cumulative)

    "max_discharging_power_today": (0, 3000, 1000),  # 0-3000W, no max change (max value)

    

    # Controller sensors

    "controller_temperature": (-40, 85, 4),  # -40 to 85°C, max change 20°C

}

