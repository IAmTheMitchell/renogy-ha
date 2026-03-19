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
    DEFAULT_CRITICAL_RSSI,
    DEFAULT_DEVICE_TYPE,
    DEFAULT_RSSI_TREND_STABLE_THRESHOLD,
    DEFAULT_WARN_RSSI,
    DOMAIN,
    LOGGER,
    RENOGY_BT_PREFIX,
    RENOGY_INVERTER_PREFIX,
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

# Inverter-specific sensor keys
KEY_AC_OUTPUT_VOLTAGE = "ac_output_voltage"
KEY_AC_OUTPUT_CURRENT = "ac_output_current"
KEY_AC_OUTPUT_FREQUENCY = "ac_output_frequency"
KEY_INPUT_FREQUENCY = "input_frequency"
KEY_LOAD_ACTIVE_POWER = "load_active_power"
KEY_LOAD_APPARENT_POWER = "load_apparent_power"
KEY_LOAD_PERCENTAGE = "load_percentage"
KEY_TEMPERATURE = "temperature"

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

# SHUNT300-specific sensor keys (expand as needed)
KEY_SHUNT_VOLTAGE = "shunt_voltage"
KEY_SHUNT_CURRENT = "shunt_current"
KEY_SHUNT_POWER = "shunt_power"
KEY_SHUNT_SOC = "shunt_soc"
KEY_SHUNT_ENERGY_CHARGED_TOTAL = "energy_charged_total"
KEY_SHUNT_ENERGY_DISCHARGED_TOTAL = "energy_discharged_total"
KEY_SHUNT_ESTIMATED_ENERGY = "estimated_energy_kwh"
KEY_SHUNT_STATUS = "shunt_status"
KEY_SHUNT_VERBOSE = "verbose"
KEY_SHUNT_STATUS_SOURCE = "status_source"
KEY_SHUNT_ENERGY_SOURCE = "energy_source"
KEY_SHUNT_DECODE_CONFIDENCE = "decode_confidence"
KEY_SHUNT_READING_VERIFIED = "reading_verified"
KEY_SHUNT_TEMPERATURE_1 = "temp_1"
KEY_SHUNT_TEMPERATURE_2 = "temp_2"
KEY_SHUNT_TEMPERATURE_3 = "temp_3"
KEY_SHUNT_STARTER_VOLTAGE = "starter_battery_voltage"
KEY_SHUNT_HIST_1 = "hist_1"
KEY_SHUNT_HIST_2 = "hist_2"
KEY_SHUNT_HIST_3 = "hist_3"
KEY_SHUNT_HIST_4 = "hist_4"
KEY_SHUNT_HIST_5 = "hist_5"
KEY_SHUNT_HIST_6 = "hist_6"
KEY_SHUNT_ADDITIONAL_VALUE = "additional_value"
KEY_SHUNT_SEQUENCE = "sequence"

# Device health sensor key
KEY_HEALTH_STATUS = "health_status"
KEY_RSSI_TREND = "rssi_trend"
KEY_AGGREGATE_HEALTH_STATUS = "aggregate_health_status"

# Inverter-specific sensor keys
KEY_AC_OUTPUT_VOLTAGE = "ac_output_voltage"
KEY_AC_OUTPUT_CURRENT = "ac_output_current"
KEY_AC_OUTPUT_FREQUENCY = "ac_output_frequency"
KEY_INPUT_FREQUENCY = "input_frequency"
KEY_LOAD_ACTIVE_POWER = "load_active_power"
KEY_LOAD_APPARENT_POWER = "load_apparent_power"
KEY_LOAD_PERCENTAGE = "load_percentage"
KEY_TEMPERATURE = "temperature"
SHUNT_ESTIMATED_CAPACITY_KWH = 1.28
AGGREGATE_HEALTH_SENSOR_KEY = "__aggregate_health_sensor__"


def _shunt_word_value(
    data: Dict[str, Any], index: int, scale: float = 1000.0
) -> float | None:
    """Return scaled value from shunt raw_words at index when available."""
    raw_words = data.get("raw_words")
    if not isinstance(raw_words, list) or index >= len(raw_words):
        return None
    return round(float(raw_words[index]) / scale, 3)


def _compute_health_status(
    coordinator: RenogyActiveBluetoothCoordinator,
    device: RenogyBLEDevice | None,
) -> str:
    """Compute overall device health status."""
    if not coordinator.last_update_success:
        return "disconnected"

    if device and hasattr(device, "is_available") and not device.is_available:
        return "disconnected"

    warn_rssi = getattr(coordinator, "warn_rssi", DEFAULT_WARN_RSSI)
    critical_rssi = getattr(coordinator, "critical_rssi", DEFAULT_CRITICAL_RSSI)
    if not isinstance(warn_rssi, (int, float)):
        warn_rssi = DEFAULT_WARN_RSSI
    if not isinstance(critical_rssi, (int, float)):
        critical_rssi = DEFAULT_CRITICAL_RSSI

    rssi = (
        device.rssi
        if device and isinstance(getattr(device, "rssi", None), (int, float))
        else None
    )

    if rssi is not None:
        if rssi <= critical_rssi:
            return "critical"
        if rssi <= warn_rssi:
            return "warn"

    auto_fallback = getattr(coordinator, "_shunt_auto_fallback_active", False)
    if isinstance(auto_fallback, bool) and auto_fallback:
        return "warn"

    failures = getattr(coordinator, "_shunt_listener_failures", 0)
    if isinstance(failures, int) and failures > 0:
        return "warn"

    return "healthy"


def _compute_rssi_trend(samples: list[float]) -> str:
    """Return RSSI trend based on a rolling sample window."""
    if len(samples) < 2:
        return "unknown"

    delta = samples[-1] - samples[0]
    threshold = DEFAULT_RSSI_TREND_STABLE_THRESHOLD
    if abs(delta) < threshold:
        return "stable"
    if delta > 0:
        return "improving"
    return "declining"


def _resolve_device_display_name(
    *,
    coordinator: RenogyActiveBluetoothCoordinator,
    device: RenogyBLEDevice | None,
    fallback: str,
) -> str:
    """Return the display name for a device, honoring any alias."""
    alias = getattr(coordinator, "device_alias", "")
    if isinstance(alias, str) and alias.strip():
        return alias.strip()
    if device and isinstance(device.name, str) and device.name.strip():
        return device.name
    return fallback


def _normalize_shunt_energy_source(data: Dict[str, Any]) -> str:
    """Normalize shunt energy source for display."""
    energy_source = data.get(KEY_SHUNT_ENERGY_SOURCE)
    if isinstance(energy_source, str):
        normalized = energy_source.strip().lower()
        if normalized in {"unknown", "n/a", "na", ""}:
            energy_source = None

    if energy_source is None:
        if (
            data.get(KEY_SHUNT_ENERGY_CHARGED_TOTAL) is not None
            or data.get(KEY_SHUNT_ENERGY_DISCHARGED_TOTAL) is not None
        ):
            return "integrated"
        return "unavailable"

    return str(energy_source)


@dataclass(frozen=True)
class RenogyBLESensorDescription(SensorEntityDescription):
    """Describes a Renogy BLE sensor."""

    # Function to extract value from the device's parsed data
    value_fn: Optional[Callable[[Dict[str, Any]], Any]] = None


# SHUNT300 sensor entity descriptions (expand as needed)
SHUNT300_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_SHUNT_VOLTAGE,
        name="Shunt Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: (
            round(float(data[KEY_SHUNT_VOLTAGE]), 2)
            if data.get(KEY_SHUNT_VOLTAGE) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_CURRENT,
        name="Shunt Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: (
            round(float(data[KEY_SHUNT_CURRENT]), 2)
            if data.get(KEY_SHUNT_CURRENT) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_POWER,
        name="Shunt Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: (
            round(float(data[KEY_SHUNT_POWER]), 1)
            if data.get(KEY_SHUNT_POWER) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_SOC,
        name="Shunt State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_SHUNT_SOC),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_ENERGY_CHARGED_TOTAL,
        name="Shunt Charged Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_SHUNT_ENERGY_CHARGED_TOTAL),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_ENERGY_DISCHARGED_TOTAL,
        name="Shunt Discharged Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get(KEY_SHUNT_ENERGY_DISCHARGED_TOTAL),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_STATUS,
        name="Shunt Charge Status",
        device_class=None,
        value_fn=lambda data: (
            "charging"
            if data.get(KEY_SHUNT_CURRENT, 0) is not None
            and data.get(KEY_SHUNT_CURRENT, 0) > 0.05
            else "discharging"
            if data.get(KEY_SHUNT_CURRENT, 0) is not None
            and data.get(KEY_SHUNT_CURRENT, 0) < -0.05
            else "idle"
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_TEMPERATURE_1,
        name="Shunt Temperature 1",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            round(float(data[KEY_SHUNT_TEMPERATURE_1]), 1)
            if data.get(KEY_SHUNT_TEMPERATURE_1) is not None
            else round(float(data["battery_temperature"]), 1)
            if data.get("battery_temperature") is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_TEMPERATURE_2,
        name="Shunt Temperature 2",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_TEMPERATURE_2)
            if data.get(KEY_SHUNT_TEMPERATURE_2) is not None
            else _shunt_word_value(data, 38)
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_TEMPERATURE_3,
        name="Shunt Temperature 3",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_TEMPERATURE_3)
            if data.get(KEY_SHUNT_TEMPERATURE_3) is not None
            else _shunt_word_value(data, 40)
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_STARTER_VOLTAGE,
        name="Shunt Starter Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            round(float(data[KEY_SHUNT_STARTER_VOLTAGE]), 2)
            if data.get(KEY_SHUNT_STARTER_VOLTAGE) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_ESTIMATED_ENERGY,
        name="Shunt Estimated Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            round(
                (float(data[KEY_SHUNT_SOC]) / 100.0) * SHUNT_ESTIMATED_CAPACITY_KWH, 3
            )
            if data.get(KEY_SHUNT_SOC) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_1,
        name="Shunt Historical Value 1",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_1) or _shunt_word_value(data, 42),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_2,
        name="Shunt Historical Value 2",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_2) or _shunt_word_value(data, 44),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_3,
        name="Shunt Historical Value 3",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_3) or _shunt_word_value(data, 46),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_4,
        name="Shunt Historical Value 4",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_4) or _shunt_word_value(data, 48),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_5,
        name="Shunt Historical Value 5",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_5) or _shunt_word_value(data, 50),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_HIST_6,
        name="Shunt Historical Value 6",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_HIST_6) or _shunt_word_value(data, 52),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_ADDITIONAL_VALUE,
        name="Shunt Additional Value",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_ADDITIONAL_VALUE)
            if data.get(KEY_SHUNT_ADDITIONAL_VALUE) is not None
            else _shunt_word_value(data, 53) or _shunt_word_value(data, 34)
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_SEQUENCE,
        name="Shunt Packet Sequence",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_SEQUENCE)
            if data.get(KEY_SHUNT_SEQUENCE) is not None
            else int(data["raw_words"][-1])
            if isinstance(data.get("raw_words"), list) and data.get("raw_words")
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_VERBOSE,
        name="Shunt Verbose Mode",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            "enabled"
            if str(data.get(KEY_SHUNT_VERBOSE, "")).strip().lower()
            in {"1", "true", "yes", "on"}
            else "disabled"
            if str(data.get(KEY_SHUNT_VERBOSE, "")).strip().lower()
            in {"0", "false", "no", "off"}
            else "unknown"
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_STATUS_SOURCE,
        name="Shunt Status Source",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get(KEY_SHUNT_STATUS_SOURCE),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_ENERGY_SOURCE,
        name="Shunt Energy Source",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_normalize_shunt_energy_source,
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_DECODE_CONFIDENCE,
        name="Shunt Decode Confidence",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_DECODE_CONFIDENCE) or data.get("conf") or "unknown"
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_SHUNT_READING_VERIFIED,
        name="Shunt Reading Verified",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.get(KEY_SHUNT_READING_VERIFIED)
            if data.get(KEY_SHUNT_READING_VERIFIED) is not None
            else data.get("verified")
        ),
    ),
)

HEALTH_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_HEALTH_STATUS,
        name="Device Health",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=None,
    ),
    RenogyBLESensorDescription(
        key=KEY_RSSI_TREND,
        name="RSSI Trend",
        device_class=None,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=None,
    ),
)

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


BATTERY_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_BATTERY_VOLTAGE,
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_CURRENT,
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_PERCENTAGE,
        name="Battery Percentage",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_PERCENTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_BATTERY_TEMPERATURE,
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
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
        value_fn=lambda data: data.get(KEY_PV_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_PV_CURRENT,
        name="PV Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_PV_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_PV_POWER,
        name="PV Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
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
        value_fn=lambda data: data.get(KEY_LOAD_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_CURRENT,
        name="Load Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_LOAD_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_POWER,
        name="Load Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
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
# Inverter sensors
INVERTER_SENSORS: tuple[RenogyBLESensorDescription, ...] = (
    RenogyBLESensorDescription(
        key=KEY_BATTERY_VOLTAGE,
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_BATTERY_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_AC_OUTPUT_VOLTAGE,
        name="AC Output Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_AC_OUTPUT_VOLTAGE),
    ),
    RenogyBLESensorDescription(
        key=KEY_AC_OUTPUT_CURRENT,
        name="AC Output Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_AC_OUTPUT_CURRENT),
    ),
    RenogyBLESensorDescription(
        key=KEY_AC_OUTPUT_FREQUENCY,
        name="AC Output Frequency",
        native_unit_of_measurement="Hz",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_AC_OUTPUT_FREQUENCY),
    ),
    RenogyBLESensorDescription(
        key=KEY_INPUT_FREQUENCY,
        name="Input Frequency",
        native_unit_of_measurement="Hz",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_INPUT_FREQUENCY),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_ACTIVE_POWER,
        name="Load Active Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_LOAD_ACTIVE_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_APPARENT_POWER,
        name="Load Apparent Power",
        native_unit_of_measurement="VA",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_LOAD_APPARENT_POWER),
    ),
    RenogyBLESensorDescription(
        key=KEY_LOAD_PERCENTAGE,
        name="Load Percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            round((data.get(KEY_LOAD_ACTIVE_POWER, 0) / 2000) * 100, 1)
            if data.get(KEY_LOAD_ACTIVE_POWER) is not None
            else None
        ),
    ),
    RenogyBLESensorDescription(
        key=KEY_TEMPERATURE,
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get(KEY_TEMPERATURE),
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
        "Health": HEALTH_SENSORS,
    },
    DeviceType.DCC.value: {
        "Battery": DCC_BATTERY_SENSORS,
        "Alternator": DCC_ALTERNATOR_SENSORS,
        "Solar": DCC_SOLAR_SENSORS,
        "Status": DCC_STATUS_SENSORS,
        "Statistics": DCC_STATISTICS_SENSORS,
        "Diagnostic": DCC_DIAGNOSTIC_SENSORS,
        "Health": HEALTH_SENSORS,
    },
    DeviceType.SHUNT300.value: {
        "Shunt": SHUNT300_SENSORS,
        "Health": HEALTH_SENSORS,
    },
    DeviceType.INVERTER.value: {
        "Inverter": INVERTER_SENSORS,
        "Health": HEALTH_SENSORS,
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

    # Now create entities with the best name we have
    if coordinator.device and (
        coordinator.device.name.startswith(RENOGY_BT_PREFIX)
        or coordinator.device.name.startswith(RENOGY_INVERTER_PREFIX)
        or not coordinator.device.name.startswith("Unknown")
    ):
        LOGGER.info("Creating entities with device name: %s", coordinator.device.name)
        device_entities = create_device_entities(
            coordinator, coordinator.device, device_type
        )
    else:
        LOGGER.debug(
            "Creating sensor entities without waiting for a resolved device name"
        )
        LOGGER.info("Creating entities with coordinator only (generic name)")
        device_entities = create_coordinator_entities(coordinator, device_type)

    # Add all entities to Home Assistant
    if device_entities:
        LOGGER.debug("Adding %s entities", len(device_entities))
        async_add_entities(device_entities)
    else:
        LOGGER.warning("No entities were created")

    aggregate_sensor = _get_or_create_aggregate_sensor(hass, async_add_entities)
    remove_aggregate_listener = aggregate_sensor.attach_entry(config_entry.entry_id)
    config_entry.async_on_unload(remove_aggregate_listener)


def _get_or_create_aggregate_sensor(
    hass: HomeAssistant, async_add_entities: AddEntitiesCallback
) -> "RenogyAggregateHealthSensor":
    """Return the singleton aggregate health sensor for this integration."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    existing = domain_data.get(AGGREGATE_HEALTH_SENSOR_KEY)
    if isinstance(existing, RenogyAggregateHealthSensor):
        return existing

    aggregate = RenogyAggregateHealthSensor(hass)
    domain_data[AGGREGATE_HEALTH_SENSOR_KEY] = aggregate
    async_add_entities([aggregate])
    return aggregate


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
            display_name = _resolve_device_display_name(
                coordinator=coordinator,
                device=device,
                fallback=f"Renogy {device_type.capitalize()}",
            )
            self._attr_name = f"{display_name} {description.name}"

            # Properly set up device_info for the device registry
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=display_name,
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {device.address}",
                sw_version=device_type.capitalize(),
                # Add device type as software version for clarity.
            )
        else:
            # If we don't have a device yet, use coordinator address for unique ID
            self._attr_unique_id = f"{coordinator.address}_{description.key}"
            display_name = _resolve_device_display_name(
                coordinator=coordinator,
                device=None,
                fallback=f"Renogy {device_type.capitalize()}",
            )
            self._attr_name = f"{display_name} {description.name}"

            # Set up basic device info based on coordinator
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=display_name,
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
            display_name = _resolve_device_display_name(
                coordinator=self.coordinator,
                device=self._device,
                fallback=f"Renogy {self._device_type.capitalize()}",
            )
            self._attr_name = f"{display_name} {self.entity_description.name}"

            # And device_info
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._device.address)},
                name=display_name,
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
        # Use cached value if available
        if self._attr_native_value is not None:
            return self._attr_native_value

        if self.entity_description.key == KEY_HEALTH_STATUS:
            value = _compute_health_status(self.coordinator, self.device)
            self._attr_native_value = value
            return value
        if self.entity_description.key == KEY_RSSI_TREND:
            samples = getattr(self.coordinator, "_rssi_samples", [])
            trend = _compute_rssi_trend(list(samples))
            self._attr_native_value = trend
            return trend

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
                        except ValueError, TypeError:
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

        if self._device_type == DeviceType.SHUNT300.value:
            shunt_data = None
            if self.device and self.device.parsed_data:
                shunt_data = self.device.parsed_data
            elif self.coordinator.data:
                shunt_data = self.coordinator.data

            if shunt_data:
                if "rssi" not in attrs:
                    attrs["rssi"] = "N/A"

                verbose_value = shunt_data.get(KEY_SHUNT_VERBOSE)
                if verbose_value is not None:
                    verbose_normalized = str(verbose_value).strip().lower()
                    attrs["verbose_mode"] = (
                        "enabled"
                        if verbose_normalized in {"1", "true", "yes", "on"}
                        else "disabled"
                        if verbose_normalized in {"0", "false", "no", "off"}
                        else "unknown"
                    )

                status_source = shunt_data.get(KEY_SHUNT_STATUS_SOURCE)
                if status_source is None:
                    status_source = (
                        "derived_current"
                        if shunt_data.get(KEY_SHUNT_CURRENT) is not None
                        else "unknown"
                    )
                attrs["status_source"] = status_source

                attrs["energy_source"] = _normalize_shunt_energy_source(shunt_data)

                decode_confidence = shunt_data.get(KEY_SHUNT_DECODE_CONFIDENCE)
                if decode_confidence is None:
                    decode_confidence = shunt_data.get("conf")
                if decode_confidence is None:
                    decode_confidence = "unknown"
                attrs["decode_confidence"] = decode_confidence
                reading_verified = shunt_data.get(KEY_SHUNT_READING_VERIFIED)
                if reading_verified is None:
                    reading_verified = shunt_data.get("verified")
                if reading_verified is not None:
                    attrs["reading_verified"] = reading_verified

                coordinator = self.coordinator
                connection_mode = getattr(coordinator, "shunt_connection_mode", None)
                attrs["shunt_connection_mode"] = (
                    connection_mode if isinstance(connection_mode, str) else "unknown"
                )
                listener_task = getattr(coordinator, "_shunt_listener_task", None)
                attrs["shunt_listener_active"] = isinstance(listener_task, asyncio.Task)
                failures = getattr(coordinator, "_shunt_listener_failures", 0)
                attrs["shunt_listener_failures"] = (
                    failures if isinstance(failures, int) else 0
                )
                last_success = getattr(
                    coordinator, "_shunt_listener_last_success", None
                )
                if last_success:
                    attrs["shunt_listener_last_success"] = last_success
                auto_fallback = getattr(
                    coordinator, "_shunt_auto_fallback_active", False
                )
                attrs["shunt_auto_fallback_active"] = (
                    auto_fallback if isinstance(auto_fallback, bool) else False
                )

        if self.entity_description.key == KEY_HEALTH_STATUS:
            attrs["last_update_success"] = self.coordinator.last_update_success
            attrs["warn_rssi"] = getattr(
                self.coordinator, "warn_rssi", DEFAULT_WARN_RSSI
            )
            attrs["critical_rssi"] = getattr(
                self.coordinator, "critical_rssi", DEFAULT_CRITICAL_RSSI
            )

        # Expose raw shunt payload details for troubleshooting.
        if (
            self._device_type == DeviceType.SHUNT300.value
            and self.entity_description.key == KEY_SHUNT_STATUS
            and self.device
            and self.device.parsed_data
        ):
            raw_payload = self.device.parsed_data.get("raw_payload")
            raw_words = self.device.parsed_data.get("raw_words")
            if raw_payload:
                attrs["raw_payload"] = raw_payload
            if raw_words:
                attrs["raw_words"] = raw_words

        return attrs


class RenogyAggregateHealthSensor(SensorEntity):
    """Aggregate health view across all Renogy devices."""

    _attr_name = "Renogy Health"
    _attr_unique_id = "renogy_health_aggregate"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the aggregate health sensor."""
        self.hass = hass
        self._entry_listeners: dict[str, Callable[[], None]] = {}
        self._attr_native_value = "unknown"
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._last_updated: datetime | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "aggregate_health")},
            name="Renogy Health",
            manufacturer=ATTR_MANUFACTURER,
            model="Aggregate",
        )

    def attach_entry(self, entry_id: str) -> Callable[[], None]:
        """Attach a config entry to this aggregate sensor."""
        if entry_id in self._entry_listeners:
            return lambda: None

        entry_data = self.hass.data.get(DOMAIN, {}).get(entry_id)
        coordinator = (
            entry_data.get("coordinator") if isinstance(entry_data, dict) else None
        )
        if coordinator is None:
            return lambda: None

        remove_listener = coordinator.async_add_listener(self._handle_update)
        self._entry_listeners[entry_id] = remove_listener
        self._handle_update()

        def _remove() -> None:
            remove_listener()
            self._entry_listeners.pop(entry_id, None)
            self._handle_update()

        return _remove

    def _handle_update(self) -> None:
        """Recompute aggregate state from all known devices."""
        self._last_updated = datetime.now()
        aggregate_status, attributes = self._compute_aggregate_status_and_attrs()
        self._attr_native_value = aggregate_status
        self._attr_extra_state_attributes = attributes
        self.async_write_ha_state()

    def _compute_aggregate_status_and_attrs(self) -> tuple[str, dict[str, Any]]:
        """Return aggregate status and attributes."""
        failing_devices: list[dict[str, Any]] = []
        all_devices: list[dict[str, Any]] = []
        status_counts = {
            "healthy": 0,
            "warn": 0,
            "critical": 0,
            "disconnected": 0,
        }
        total_devices = 0

        for entry_id, entry_data in self.hass.data.get(DOMAIN, {}).items():
            if entry_id == AGGREGATE_HEALTH_SENSOR_KEY:
                continue
            if not isinstance(entry_data, dict) or "coordinator" not in entry_data:
                continue

            coordinator = entry_data["coordinator"]
            device = coordinator.device
            if device is None:
                devices = entry_data.get("devices", [])
                if isinstance(devices, list) and devices:
                    device = devices[0]

            status = _compute_health_status(coordinator, device)
            total_devices += 1
            status_counts[status] = status_counts.get(status, 0) + 1

            device_summary = {
                "name": getattr(device, "name", None)
                or getattr(coordinator, "address", "unknown"),
                "address": getattr(coordinator, "address", None),
                "status": status,
                "device_type": getattr(device, "device_type", None),
                "rssi": getattr(device, "rssi", None),
            }
            all_devices.append(device_summary)

            if status != "healthy":
                failing_devices.append(device_summary)

        if total_devices == 0:
            aggregate_status = "unknown"
        elif (
            status_counts.get("critical", 0) > 0
            or status_counts.get("disconnected", 0) > 0
        ):
            aggregate_status = "critical"
        elif status_counts.get("warn", 0) > 0:
            aggregate_status = "warn"
        elif status_counts.get("healthy", 0) == total_devices:
            aggregate_status = "healthy"
        else:
            aggregate_status = "unknown"

        attributes: dict[str, Any] = {
            "last_updated": self._last_updated.isoformat()
            if self._last_updated
            else None,
            "total_devices": total_devices,
            "healthy_devices": status_counts.get("healthy", 0),
            "warn_devices": status_counts.get("warn", 0),
            "critical_devices": status_counts.get("critical", 0),
            "disconnected_devices": status_counts.get("disconnected", 0),
            "failing_devices": failing_devices,
            "all_devices": all_devices,
        }

        return aggregate_status, attributes

    @property
    def native_value(self) -> Any:
        """Return the aggregate health status."""
        return self._attr_native_value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregate health metadata."""
        return dict(self._attr_extra_state_attributes)
