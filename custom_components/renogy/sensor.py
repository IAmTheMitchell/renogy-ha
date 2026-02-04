"""Support for Renogy BLE sensors."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    RENOGY_BT_PREFIX,
    DeviceType,
)

# Registry of sensor keys
KEY_BATTERY_VOLTAGE = "battery_voltage"
KEY_BATTERY_CURRENT = "battery_current"
KEY_BATTERY_PERCENTAGE = "battery_percentage"
KEY_BATTERY_TEMPERATURE = "battery_temperature"
KEY_BATTERY_TYPE = "battery_type"
KEY_CHARGING_AMP_HOURS_TODAY = "charging_amp_hours_today"
KEY_DISCHARGING_AMP_HOURS_TODAY = "discharging_amp_hours_today"
KEY_CHARGING_STATUS = "charging_status"

KEY_PV_VOLTAGE = "pv_voltage"
KEY_PV_CURRENT = "pv_current"
KEY_PV_POWER = "pv_power"
KEY_MAX_CHARGING_POWER_TODAY = "max_charging_power_today"
KEY_POWER_GENERATION_TODAY = "power_generation_today"
KEY_POWER_GENERATION_TOTAL = "power_generation_total"

KEY_LOAD_VOLTAGE = "load_voltage"
KEY_LOAD_CURRENT = "load_current"
KEY_LOAD_POWER = "load_power"
KEY_LOAD_STATUS = "load_status"
KEY_POWER_CONSUMPTION_TODAY = "power_consumption_today"

KEY_CONTROLLER_TEMPERATURE = "controller_temperature"
KEY_DEVICE_ID = "device_id"
KEY_MODEL = "model"
KEY_MAX_DISCHARGING_POWER_TODAY = "max_discharging_power_today"

# DCC-specific sensor keys (DC-DC Charger)
KEY_BATTERY_SOC = "battery_soc"
KEY_TOTAL_CHARGING_CURRENT = "total_charging_current"
KEY_ALTERNATOR_VOLTAGE = "alternator_voltage"
KEY_ALTERNATOR_CURRENT = "alternator_current"
KEY_ALTERNATOR_POWER = "alternator_power"
KEY_SOLAR_VOLTAGE = "solar_voltage"
KEY_SOLAR_CURRENT = "solar_current"
KEY_SOLAR_POWER = "solar_power"
KEY_DAILY_MIN_BATTERY_VOLTAGE = "daily_min_battery_voltage"
KEY_DAILY_MAX_BATTERY_VOLTAGE = "daily_max_battery_voltage"
KEY_DAILY_MAX_CHARGING_CURRENT = "daily_max_charging_current"
KEY_DAILY_MAX_CHARGING_POWER = "daily_max_charging_power"
KEY_DAILY_CHARGING_AH = "daily_charging_ah"
KEY_DAILY_POWER_GENERATION = "daily_power_generation"
KEY_TOTAL_OPERATING_DAYS = "total_operating_days"
KEY_TOTAL_OVERDISCHARGE_COUNT = "total_overdischarge_count"
KEY_TOTAL_FULL_CHARGE_COUNT = "total_full_charge_count"
KEY_TOTAL_CHARGING_AH = "total_charging_ah"
KEY_TOTAL_POWER_GENERATION = "total_power_generation"
KEY_DCC_CHARGING_STATUS = "charging_status"
KEY_CHARGING_MODE = "charging_mode"
KEY_OUTPUT_POWER = "output_power"
KEY_IGNITION_STATUS = "ignition_status"
KEY_FAULT_HIGH = "fault_high"
KEY_FAULT_LOW = "fault_low"

# DCC Parameter keys (readable settings)
KEY_SYSTEM_VOLTAGE = "system_voltage"
KEY_OVERVOLTAGE_THRESHOLD = "overvoltage_threshold"
KEY_CHARGING_LIMIT_VOLTAGE = "charging_limit_voltage"
KEY_EQUALIZATION_VOLTAGE = "equalization_voltage"
KEY_BOOST_VOLTAGE = "boost_voltage"
KEY_FLOAT_VOLTAGE = "float_voltage"
KEY_BOOST_RETURN_VOLTAGE = "boost_return_voltage"
KEY_OVERDISCHARGE_RETURN_VOLTAGE = "overdischarge_return_voltage"
KEY_UNDERVOLTAGE_WARNING = "undervoltage_warning"
KEY_OVERDISCHARGE_VOLTAGE = "overdischarge_voltage"
KEY_DISCHARGE_LIMIT_VOLTAGE = "discharge_limit_voltage"
KEY_OVERDISCHARGE_DELAY = "overdischarge_delay"
KEY_EQUALIZATION_TIME = "equalization_time"
KEY_BOOST_TIME = "boost_time"
KEY_EQUALIZATION_INTERVAL = "equalization_interval"
KEY_TEMPERATURE_COMPENSATION = "temperature_compensation"
KEY_REVERSE_CHARGING_VOLTAGE = "reverse_charging_voltage"
KEY_SOLAR_CUTOFF_CURRENT = "solar_cutoff_current"


@dataclass
class RenogyBLESensorDescription(SensorEntityDescription):
    """Describes a Renogy BLE sensor."""

    # Function to extract value from the device's parsed data
    value_fn: Optional[Callable[[Dict[str, Any]], Any]] = None


BATTERY_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_BATTERY_VOLTAGE,
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_CURRENT,
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_BATTERY_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_PERCENTAGE,
        name="Battery Percentage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_BATTERY_PERCENTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_TEMPERATURE,
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_BATTERY_TEMPERATURE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_TYPE,
        name="Battery Type",
        device_class=None,
        value_fn=lambda data: data.get(KEY_BATTERY_TYPE),
    ),
    RenogyBLESensorDescription(
        key=KEY_CHARGING_AMP_HOURS_TODAY,
        name="Charging Amp Hours Today",
        native_unit_of_measurement="Ah",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_CHARGING_AMP_HOURS_TODAY),
    ),
    RenogyBLESensorDescription(
        key=KEY_DISCHARGING_AMP_HOURS_TODAY,
        name="Discharging Amp Hours Today",
        native_unit_of_measurement="Ah",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_DISCHARGING_AMP_HOURS_TODAY),
    ),
    RenogyBLESensorDescription(
        key=KEY_CHARGING_STATUS,
        name="Charging Status",
        device_class=None,
        value_fn=lambda data: data.get(KEY_CHARGING_STATUS),
    ),
)

PV_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_PV_VOLTAGE,
        name="PV Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_PV_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_PV_CURRENT,
        name="PV Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_PV_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_PV_POWER,
        name="PV Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_PV_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_MAX_CHARGING_POWER_TODAY,
        name="Max Charging Power Today",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_MAX_CHARGING_POWER_TODAY),
    ),
    RenogyBLESensorDescription(
        key=KEY_POWER_GENERATION_TODAY,
        name="Power Generation Today",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_POWER_GENERATION_TODAY),
    ),
    RenogyBLESensorDescription(
        key=KEY_POWER_GENERATION_TOTAL,
        name="Power Generation Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: (
            None
            if data.get(KEY_POWER_GENERATION_TOTAL) is None
            else data.get(KEY_POWER_GENERATION_TOTAL) / 1000
        ),
    ),
)

LOAD_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_LOAD_VOLTAGE,
        name="Load Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_LOAD_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_CURRENT,
        name="Load Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get(KEY_LOAD_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_POWER,
        name="Load Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_LOAD_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_STATUS,
        name="Load Status",
        device_class=None,
        value_fn=lambda data: data.get(KEY_LOAD_STATUS),
    ),
    RenogyBLESensorDescription(
        key=KEY_POWER_CONSUMPTION_TODAY,
        name="Power Consumption Today",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_POWER_CONSUMPTION_TODAY),
    ),
)

CONTROLLER_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_CONTROLLER_TEMPERATURE,
        name="Controller Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_CONTROLLER_TEMPERATURE),
    ),
    RenogyBLESensorDescription(
        key=KEY_DEVICE_ID,
        name="Device ID",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_DEVICE_ID),
    ),
    RenogyBLESensorDescription(
        key=KEY_MODEL,
        name="Model",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_MODEL),
    ),
    RenogyBLESensorDescription(
        key=KEY_MAX_DISCHARGING_POWER_TODAY,
        name="Max Discharging Power Today",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get(KEY_MAX_DISCHARGING_POWER_TODAY),
    ),
)

# DCC (DC-DC Charger) specific sensors
# These use different naming to avoid confusion with solar charge controllers
DCC_BATTERY_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_BATTERY_SOC,
        name="House Battery SOC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_SOC),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_VOLTAGE,
        name="House Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_CHARGING_CURRENT,
        name="Total Charging Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_TOTAL_CHARGING_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_TYPE,
        name="Battery Type",
        device_class=None,
        value_fn=lambda data: data.get(KEY_BATTERY_TYPE),
    ),
    RenogyBLESensorDescription(
        key=KEY_CONTROLLER_TEMPERATURE,
        name="Controller Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_CONTROLLER_TEMPERATURE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_TEMPERATURE,
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_TEMPERATURE),
    ),
)

DCC_ALTERNATOR_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_ALTERNATOR_VOLTAGE,
        name="Alternator Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_ALTERNATOR_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_ALTERNATOR_CURRENT,
        name="Alternator Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_ALTERNATOR_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_ALTERNATOR_POWER,
        name="Alternator Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_ALTERNATOR_POWER),
    ),
)

DCC_SOLAR_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_SOLAR_VOLTAGE,
        name="Solar Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_SOLAR_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_SOLAR_CURRENT,
        name="Solar Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_SOLAR_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_SOLAR_POWER,
        name="Solar Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_SOLAR_POWER),
    ),
)

DCC_STATUS_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_DCC_CHARGING_STATUS,
        name="Charging Status",
        device_class=None,
        value_fn=lambda data: data.get(KEY_DCC_CHARGING_STATUS),
    ),
    RenogyBLESensorDescription(
        key=KEY_CHARGING_MODE,
        name="Charging Mode",
        device_class=None,
        value_fn=lambda data: data.get(KEY_CHARGING_MODE),
    ),
    RenogyBLESensorDescription(
        key=KEY_OUTPUT_POWER,
        name="Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_OUTPUT_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_IGNITION_STATUS,
        name="Ignition Status",
        device_class=None,
        value_fn=lambda data: data.get(KEY_IGNITION_STATUS),
    ),
)

DCC_STATISTICS_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_DAILY_MIN_BATTERY_VOLTAGE,
        name="Daily Min Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_DAILY_MIN_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_DAILY_MAX_BATTERY_VOLTAGE,
        name="Daily Max Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_DAILY_MAX_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_DAILY_MAX_CHARGING_CURRENT,
        name="Daily Max Charging Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_DAILY_MAX_CHARGING_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_DAILY_MAX_CHARGING_POWER,
        name="Daily Max Charging Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_DAILY_MAX_CHARGING_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_DAILY_CHARGING_AH,
        name="Daily Charging Ah",
        native_unit_of_measurement="Ah",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_DAILY_CHARGING_AH),
    ),
    RenogyBLESensorDescription(
        key=KEY_DAILY_POWER_GENERATION,
        name="Daily Power Generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_DAILY_POWER_GENERATION),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_OPERATING_DAYS,
        name="Total Operating Days",
        native_unit_of_measurement="days",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_TOTAL_OPERATING_DAYS),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_CHARGING_AH,
        name="Total Charging Ah",
        native_unit_of_measurement="Ah",
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_TOTAL_CHARGING_AH),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_POWER_GENERATION,
        name="Total Power Generation",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_TOTAL_POWER_GENERATION),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_OVERDISCHARGE_COUNT,
        name="Total Overdischarge Count",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_TOTAL_OVERDISCHARGE_COUNT),
    ),
    RenogyBLESensorDescription(
        key=KEY_TOTAL_FULL_CHARGE_COUNT,
        name="Total Full Charge Count",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_TOTAL_FULL_CHARGE_COUNT),
    ),
)

DCC_DIAGNOSTIC_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_DEVICE_ID,
        name="Device ID",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_DEVICE_ID),
    ),
    RenogyBLESensorDescription(
        key=KEY_MODEL,
        name="Model",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_MODEL),
    ),
    RenogyBLESensorDescription(
        key=KEY_SYSTEM_VOLTAGE,
        name="System Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SYSTEM_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_FAULT_HIGH,
        name="Fault Code High",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_FAULT_HIGH),
    ),
    RenogyBLESensorDescription(
        key=KEY_FAULT_LOW,
        name="Fault Code Low",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_FAULT_LOW),
    ),
)

# All DCC sensors combined
DCC_ALL_SENSORS = (
    DCC_BATTERY_SENSORS
    + DCC_ALTERNATOR_SENSORS
    + DCC_SOLAR_SENSORS
    + DCC_STATUS_SENSORS
    + DCC_STATISTICS_SENSORS
    + DCC_DIAGNOSTIC_SENSORS
)

# SHUNT-specific sensors (Smart Battery Management System)
SHUNT_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("battery_voltage"),
    ),
    RenogyBLESensorDescription(
        key="battery_current",
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("battery_current"),
    ),
    RenogyBLESensorDescription(
        key="power",
        name="Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("power"),
    ),
    RenogyBLESensorDescription(
        key="state_of_charge",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("state_of_charge"),
    ),
    RenogyBLESensorDescription(
        key="starter_voltage",
        name="Starter Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("starter_voltage"),
    ),
)

# All sensors combined (for controller type)
ALL_SENSORS = BATTERY_SENSORS + PV_SENSORS + LOAD_SENSORS + CONTROLLER_SENSORS

# Sensor mapping by device type
SENSORS_BY_DEVICE_TYPE = {
    DeviceType.CONTROLLER.value: {
        "Battery": BATTERY_SENSORS,
        "PV": PV_SENSORS,
        "Load": LOAD_SENSORS,
        "Controller": CONTROLLER_SENSORS,
    },
    DeviceType.DCC.value: {
        "Battery": DCC_BATTERY_SENSORS,
        "Alternator": DCC_ALTERNATOR_SENSORS,
        "Solar": DCC_SOLAR_SENSORS,
        "Status": DCC_STATUS_SENSORS,
        "Statistics": DCC_STATISTICS_SENSORS,
        "Diagnostic": DCC_DIAGNOSTIC_SENSORS,
    },
    DeviceType.SHUNT.value: {
        "SHUNT": SHUNT_SENSORS,
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE sensors."""
    LOGGER.debug("Setting up Renogy BLE sensors for entry: %s", config_entry.entry_id)

    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    # Get device type from config
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
    LOGGER.debug("Setting up sensors for device type: %s", device_type)

    # Try to wait for a real device name before creating entities
    # This helps ensure entity IDs will match the real device name
    if (
        not coordinator.device
        or coordinator.device.name.startswith("Unknown")
        or not coordinator.device.name.startswith(RENOGY_BT_PREFIX)
    ):
        LOGGER.debug("Waiting for real device name before creating entities...")
        # Force an immediate refresh to try getting device info
        await coordinator.async_request_refresh()

        # Wait for a short time to see if we can get the real device name
        # We'll wait up to 10 seconds, checking every second
        real_name_found = False
        for _ in range(10):
            await asyncio.sleep(1)
            if coordinator.device and coordinator.device.name.startswith(
                RENOGY_BT_PREFIX
            ):
                LOGGER.debug("Real device name found: %s", coordinator.device.name)
                real_name_found = True
                break

        if not real_name_found:
            LOGGER.debug(
                "No real device name found after waiting. "
                "Using generic name for entities."
            )

    # Now create entities with the best name we have
    if coordinator.device and (
        coordinator.device.name.startswith(RENOGY_BT_PREFIX)
        or not coordinator.device.name.startswith("Unknown")
    ):
        LOGGER.info("Creating entities with device name: %s", coordinator.device.name)
        device_entities = create_device_entities(
            coordinator, coordinator.device, device_type
        )
    else:
        LOGGER.info("Creating entities with coordinator only (generic name)")
        device_entities = create_coordinator_entities(coordinator, device_type)

    # Add all entities to Home Assistant
    if device_entities:
        LOGGER.debug("Adding %s entities", len(device_entities))
        async_add_entities(device_entities)
    else:
        LOGGER.warning("No entities were created")


def create_entities_helper(
    coordinator: RenogyActiveBluetoothCoordinator,
    device: Optional[RenogyBLEDevice],
    device_type: str = DEFAULT_DEVICE_TYPE,
) -> List[RenogyBLESensor]:
    """Create sensor entities with provided coordinator and optional device."""
    entities = []

    # Get sensors for the specific device type, fallback to controller sensors
    sensor_groups = SENSORS_BY_DEVICE_TYPE.get(
        device_type,
        SENSORS_BY_DEVICE_TYPE[DeviceType.CONTROLLER.value],
    )

    # Group sensors by category
    for category_name, sensor_list in sensor_groups.items():
        for description in sensor_list:
            sensor = RenogyBLESensor(
                coordinator, device, description, category_name, device_type
            )
            entities.append(sensor)

    return entities


def create_coordinator_entities(
    coordinator: RenogyActiveBluetoothCoordinator,
    device_type: str = DEFAULT_DEVICE_TYPE,
) -> List[RenogyBLESensor]:
    """Create sensor entities with just the coordinator (no device yet)."""
    entities = create_entities_helper(coordinator, None, device_type)
    LOGGER.info("Created %s entities with coordinator only", len(entities))
    return entities


def create_device_entities(
    coordinator: RenogyActiveBluetoothCoordinator,
    device: RenogyBLEDevice,
    device_type: str = DEFAULT_DEVICE_TYPE,
) -> List[RenogyBLESensor]:
    """Create sensor entities for a device."""
    entities = create_entities_helper(coordinator, device, device_type)
    LOGGER.info("Created %s entities for device %s", len(entities), device.name)
    return entities


class RenogyBLESensor(PassiveBluetoothCoordinatorEntity, SensorEntity):
    """Representation of a Renogy BLE sensor."""

    entity_description: RenogyBLESensorDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        description: RenogyBLESensorDescription,
        category: str | None = None,
        device_type: str = DEFAULT_DEVICE_TYPE,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device = device
        self._category = category
        self._device_type = device_type
        self._attr_native_value = None

        # Generate a device model name that includes the device type
        device_model = f"Renogy {device_type.capitalize()}"
        if device and device.parsed_data and KEY_MODEL in device.parsed_data:
            device_model = device.parsed_data[KEY_MODEL]

        # Device-dependent properties
        if device:
            self._attr_unique_id = f"{device.address}_{description.key}"
            self._attr_name = f"{device.name} {description.name}"

            # Properly set up device_info for the device registry
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {device.address}",
                sw_version=device_type.capitalize(),
                # Add device type as software version for clarity.
            )
        else:
            # If we don't have a device yet, use coordinator address for unique ID
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            self._attr_name = f"Renogy {description.name}"

            # Set up basic device info based on coordinator
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.capitalize()}",
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {coordinator.address}",
                sw_version=device_type.capitalize(),
                # Add device type as software version for clarity.
            )

        self._last_updated = None

    @property
    def device(self) -> Optional[RenogyBLEDevice]:
        """Get the current device - either stored or from coordinator."""
        if self._device:
            return self._device

        # Try to get device from coordinator
        if hasattr(self.coordinator, "device") and self.coordinator.device:
            self._device = self.coordinator.device

            # Generate a device model name that includes the device type
            device_model = f"Renogy {self._device_type.capitalize()}"
            if self._device.parsed_data and KEY_MODEL in self._device.parsed_data:
                device_model = self._device.parsed_data[KEY_MODEL]

            # Update our unique_id to match the actual device
            self._attr_unique_id = (
                f"{self._device.address}_{self.entity_description.key}"
            )
            # Also update our name
            self._attr_name = f"{self._device.name} {self.entity_description.name}"

            # And device_info
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._device.address)},
                name=self._device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {self._device.address}",
                sw_version=self._device_type.capitalize(),
                # Add device type as software version.
            )
            LOGGER.debug("Updated device info with real name: %s", self._device.name)

        return self._device

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        # Basic coordinator availability check
        if not self.coordinator.last_update_success:
            return False

        # Check device availability if we have a device
        if self._device and not self._device.is_available:
            return False

        # For the actual data, check either the device's parsed_data or
        # coordinator's data.
        data_available = False
        if self._device and self._device.parsed_data:
            data_available = True
        elif self.coordinator.data:
            data_available = True

        return data_available

    @property
    def native_value(self) -> Any:
        """Return the sensor's value."""
        # Return None if sensor is unavailable to prevent state errors
        if not self.available:
            self._attr_native_value = None  # Clear cache when unavailable
            return None
            
        # Use cached value if available (but guard against string "unavailable")
        if self._attr_native_value is not None and self._attr_native_value != "unavailable":
            return self._attr_native_value

        device = self.device
        data = None

        # Get data from device if available, otherwise from coordinator
        if device and device.parsed_data:
            data = device.parsed_data
        elif self.coordinator.data:
            data = self.coordinator.data

        if not data:
            return None

        try:
            if self.entity_description.value_fn:
                value = self.entity_description.value_fn(data)
                
                # Guard against string "unavailable" values
                if value == "unavailable":
                    return None
                    
                # Basic type validation based on device_class
                if value is not None:
                    if self.device_class in [
                        SensorDeviceClass.VOLTAGE,
                        SensorDeviceClass.CURRENT,
                        SensorDeviceClass.TEMPERATURE,
                        SensorDeviceClass.POWER,
                    ]:
                        try:
                            value = float(value)
                            # Basic range validation
                            if value < -1000 or value > 10000:
                                LOGGER.warning(
                                    "Value %s out of reasonable range for %s",
                                    value,
                                    self.name,
                                )
                                return None
                        except (ValueError, TypeError):
                            LOGGER.warning(
                                "Invalid numeric value for %s: %s",
                                self.name,
                                value,
                            )
                            return None

                # Cache the value
                self._attr_native_value = value
                return value
        except Exception as e:
            LOGGER.warning("Error getting native value for %s: %s", self.name, e)
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug("Coordinator update for %s", self.name)

        # Clear cached value to force a refresh on next state read
        self._attr_native_value = None

        # If we don't have a device yet, check if coordinator now has one
        if (
            not self._device
            and hasattr(self.coordinator, "device")
            and self.coordinator.device
        ):
            self._device = self.coordinator.device
            # Update our unique_id and name to match the actual device
            self._attr_unique_id = (
                f"{self._device.address}_{self.entity_description.key}"
            )
            self._attr_name = f"{self._device.name} {self.entity_description.name}"

        self._last_updated = datetime.now()

        # Explicitly get our value before updating state, so it's cached
        self.native_value
        # Update entity state
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}
        if self._last_updated:
            attrs["last_updated"] = self._last_updated.isoformat()

        # Add the device's RSSI as attribute if available
        device = self.device
        if device and hasattr(device, "rssi") and device.rssi is not None:
            attrs["rssi"] = device.rssi

        # Add data source info
        if self._device and self._device.parsed_data:
            attrs["data_source"] = "device"
        elif self.coordinator.data:
            attrs["data_source"] = "coordinator"

        return attrs
