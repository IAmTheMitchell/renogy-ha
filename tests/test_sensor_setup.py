"""Tests for Renogy BLE sensor setup behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch


def _install_module_stubs() -> None:
    """Install minimal Home Assistant module stubs to import the sensor module."""
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    bluetooth_components_module = cast(
        Any, types.ModuleType("homeassistant.components.bluetooth")
    )
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_components_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    class HomeAssistant:
        """Stub HomeAssistant class for testing."""

    def callback(func: Any) -> Any:
        """Return the function unchanged for testing."""
        return func

    core_module.HomeAssistant = HomeAssistant
    core_module.callback = callback
    sys.modules["homeassistant.core"] = core_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        """Stub ConfigEntry class for testing."""

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    passive_module = cast(
        Any,
        types.ModuleType(
            "homeassistant.components.bluetooth.passive_update_coordinator"
        ),
    )

    class PassiveBluetoothCoordinatorEntity:
        """Stub PassiveBluetoothCoordinatorEntity for testing."""

        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

    passive_module.PassiveBluetoothCoordinatorEntity = PassiveBluetoothCoordinatorEntity
    sys.modules["homeassistant.components.bluetooth.passive_update_coordinator"] = (
        passive_module
    )

    sensor_module = cast(Any, types.ModuleType("homeassistant.components.sensor"))

    class SensorEntity:
        """Stub SensorEntity class for testing."""

        def async_write_ha_state(self) -> None:
            """Stub state write for testing."""
            return None

    @dataclass(frozen=True)
    class SensorEntityDescription:
        """Stub SensorEntityDescription for testing."""

        key: str | None = None
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        suggested_display_precision: int | None = None
        entity_category: str | None = None

    class SensorDeviceClass:
        """Stub sensor device classes."""

        VOLTAGE = "voltage"
        CURRENT = "current"
        POWER = "power"
        APPARENT_POWER = "apparent_power"
        FREQUENCY = "frequency"
        POWER_FACTOR = "power_factor"
        TEMPERATURE = "temperature"
        BATTERY = "battery"
        ENERGY = "energy"

    class SensorStateClass:
        """Stub sensor state classes."""

        MEASUREMENT = "measurement"
        TOTAL_INCREASING = "total_increasing"

    sensor_module.SensorEntity = SensorEntity
    sensor_module.SensorEntityDescription = SensorEntityDescription
    sensor_module.SensorDeviceClass = SensorDeviceClass
    sensor_module.SensorStateClass = SensorStateClass
    sys.modules["homeassistant.components.sensor"] = sensor_module

    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    sys.modules["homeassistant.helpers"] = helpers_module

    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )

    class DeviceInfo(dict):
        """Stub DeviceInfo that stores provided fields."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

    device_registry_module.DeviceInfo = DeviceInfo
    device_registry_module.async_get = MagicMock()
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    entity_module = cast(Any, types.ModuleType("homeassistant.helpers.entity"))

    class EntityCategory:
        """Stub entity categories."""

        DIAGNOSTIC = "diagnostic"

    entity_module.EntityCategory = EntityCategory
    sys.modules["homeassistant.helpers.entity"] = entity_module

    entity_platform_module = cast(
        Any, types.ModuleType("homeassistant.helpers.entity_platform")
    )

    class AddEntitiesCallback:
        """Stub AddEntitiesCallback for testing."""

    entity_platform_module.AddEntitiesCallback = AddEntitiesCallback
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.CONF_ADDRESS = "address"
    const_module.PERCENTAGE = "%"

    class Platform(str, Enum):
        """Stub Platform enum values for testing."""

        SENSOR = "sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"

    class UnitOfElectricCurrent:
        """Stub current units."""

        AMPERE = "A"

    class UnitOfElectricPotential:
        """Stub voltage units."""

        VOLT = "V"

    class UnitOfEnergy:
        """Stub energy units."""

        WATT_HOUR = "Wh"
        KILO_WATT_HOUR = "kWh"

    class UnitOfPower:
        """Stub power units."""

        WATT = "W"

    class UnitOfTemperature:
        """Stub temperature units."""

        CELSIUS = "C"

    const_module.Platform = Platform
    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
    const_module.UnitOfEnergy = UnitOfEnergy
    const_module.UnitOfPower = UnitOfPower
    const_module.UnitOfTemperature = UnitOfTemperature
    sys.modules["homeassistant.const"] = const_module

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyActiveBluetoothCoordinator:
        """Stub coordinator class for testing."""

    class RenogyBLEDevice:
        """Stub BLE device class for testing."""

    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    ble_module.RenogyBLEDevice = RenogyBLEDevice
    sys.modules["custom_components.renogy.ble"] = ble_module


def _load_sensor_module() -> Any:
    """Load the sensor module with stubs in place."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.sensor", None)
    sys.modules.pop("custom_components.renogy", None)
    return importlib.import_module("custom_components.renogy.sensor")


def test_sensor_setup_does_not_wait_for_named_shunt() -> None:
    """Ensure setup skips refresh/wait loop when shunt name is already available."""
    sensor_module = _load_sensor_module()

    device = MagicMock()
    device.name = "RTMShunt300A1B2"
    device.address = "AA:BB:CC:DD:EE:FF"

    coordinator = MagicMock()
    coordinator.device = device
    coordinator.address = device.address
    coordinator.async_request_refresh = AsyncMock()
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90

    device.is_available = True
    device.rssi = None

    hass = MagicMock()
    hass.data = {sensor_module.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        sensor_module.CONF_DEVICE_TYPE: sensor_module.DeviceType.SHUNT300.value
    }

    async_add_entities = MagicMock()

    with patch.object(sensor_module, "create_device_entities", return_value=[]):
        with patch.object(
            sensor_module, "create_coordinator_entities", return_value=[]
        ):
            asyncio.run(
                sensor_module.async_setup_entry(hass, config_entry, async_add_entities)
            )

    coordinator.async_request_refresh.assert_not_awaited()
    async_add_entities.assert_called_once()
    aggregate_entities = async_add_entities.call_args.args[0]
    assert len(aggregate_entities) == 1
    assert isinstance(
        aggregate_entities[0],
        sensor_module.RenogyAggregateHealthSensor,
    )


def test_sensor_setup_does_not_wait_for_unknown_device_name() -> None:
    """Ensure setup creates generic entities immediately when name is unresolved."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.device = None
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90

    hass = MagicMock()
    hass.data = {sensor_module.DOMAIN: {"entry-1": {"coordinator": coordinator}}}

    config_entry = MagicMock()
    config_entry.entry_id = "entry-1"
    config_entry.data = {
        sensor_module.CONF_DEVICE_TYPE: sensor_module.DeviceType.CONTROLLER.value
    }

    async_add_entities = MagicMock()

    with patch.object(sensor_module, "create_device_entities", return_value=[]):
        with patch.object(
            sensor_module,
            "create_coordinator_entities",
            return_value=["entity"],
        ) as create_coordinator_entities:
            asyncio.run(
                sensor_module.async_setup_entry(hass, config_entry, async_add_entities)
            )

    coordinator.async_request_refresh.assert_not_awaited()
    create_coordinator_entities.assert_called_once_with(
        coordinator, sensor_module.DeviceType.CONTROLLER.value
    )
    async_add_entities.assert_any_call(["entity"])


def test_shunt_energy_sensors_use_total_increasing_state_class() -> None:
    """Ensure shunt energy total sensors use a valid monotonic state class."""
    sensor_module = _load_sensor_module()

    shunt_energy_descriptions = [
        description
        for description in sensor_module.SHUNT300_SENSORS
        if description.key
        in {
            sensor_module.KEY_SHUNT_ENERGY_CHARGED_TOTAL,
            sensor_module.KEY_SHUNT_ENERGY_DISCHARGED_TOTAL,
        }
    ]

    assert len(shunt_energy_descriptions) == 2
    for description in shunt_energy_descriptions:
        assert description.device_class == sensor_module.SensorDeviceClass.ENERGY
        assert (
            description.state_class == sensor_module.SensorStateClass.TOTAL_INCREASING
        )


def test_shunt_estimated_energy_has_no_state_class() -> None:
    """Ensure shunt estimated energy does not use an invalid state class."""
    sensor_module = _load_sensor_module()

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_ESTIMATED_ENERGY
    )

    assert description.device_class == sensor_module.SensorDeviceClass.ENERGY
    assert description.state_class is None


def test_shunt_status_sensor_exposes_troubleshooting_attributes() -> None:
    """Ensure SHUNT300 entities expose extra troubleshooting metadata."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = True
    coordinator.data = {}

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "RTMShunt300A1B2"
    device.rssi = None
    device.parsed_data = {
        sensor_module.KEY_SHUNT_CURRENT: 1.23,
        sensor_module.KEY_SHUNT_ENERGY_CHARGED_TOTAL: 0.45,
        sensor_module.KEY_SHUNT_VERBOSE: "1",
        sensor_module.KEY_SHUNT_DECODE_CONFIDENCE: "high",
        sensor_module.KEY_SHUNT_READING_VERIFIED: True,
        "raw_payload": "deadbeef",
        "raw_words": [1, 2, 3],
    }

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_STATUS
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Shunt",
        sensor_module.DeviceType.SHUNT300.value,
    )
    attrs = entity.extra_state_attributes

    assert attrs["rssi"] == "N/A"
    assert attrs["data_source"] == "device"
    assert attrs["verbose_mode"] == "enabled"
    assert attrs["status_source"] == "derived_current"
    assert attrs["energy_source"] == "integrated"
    assert attrs["decode_confidence"] == "high"
    assert attrs["reading_verified"] is True
    assert attrs["raw_payload"] == "deadbeef"
    assert attrs["raw_words"] == [1, 2, 3]
    assert attrs["shunt_connection_mode"] == "unknown"
    assert attrs["shunt_listener_active"] is False
    assert attrs["shunt_listener_failures"] == 0
    assert attrs["shunt_auto_fallback_active"] is False


def test_shunt_status_sensor_preserves_zero_decode_confidence() -> None:
    """Ensure zero decode confidence remains visible in troubleshooting attributes."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = True
    coordinator.data = {}

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "RTMShunt300A1B2"
    device.rssi = None
    device.parsed_data = {
        sensor_module.KEY_SHUNT_CURRENT: 1.23,
        sensor_module.KEY_SHUNT_DECODE_CONFIDENCE: 0,
    }

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_STATUS
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Shunt",
        sensor_module.DeviceType.SHUNT300.value,
    )

    assert entity.extra_state_attributes["decode_confidence"] == 0


def test_shunt_temperature_1_sensor_exposes_source() -> None:
    """Ensure shunt temperature sensor reports the underlying data source."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = True
    coordinator.data = {}

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "RTMShunt300A1B2"
    device.rssi = None
    device.parsed_data = {
        sensor_module.KEY_SHUNT_TEMPERATURE_1: 22.5,
        sensor_module.KEY_BATTERY_TEMPERATURE: 18.0,
    }

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_TEMPERATURE_1
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Shunt",
        sensor_module.DeviceType.SHUNT300.value,
    )

    assert (
        entity.extra_state_attributes["temperature_1_source"] == "shunt_temperature_1"
    )


def test_shunt_temperature_1_sensor_falls_back_to_battery_temp_source() -> None:
    """Ensure shunt temperature sensor reports battery temperature fallback."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = True
    coordinator.data = {}

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "RTMShunt300A1B2"
    device.rssi = None
    device.parsed_data = {
        sensor_module.KEY_BATTERY_TEMPERATURE: 18.0,
    }

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_TEMPERATURE_1
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Shunt",
        sensor_module.DeviceType.SHUNT300.value,
    )

    assert (
        entity.extra_state_attributes["temperature_1_source"] == "battery_temperature"
    )


def test_inverter_sensor_mapping_uses_library_field_names() -> None:
    """Ensure inverter entities map directly to renogy-ble parsed field names."""
    sensor_module = _load_sensor_module()

    descriptions = {
        description.key: description for description in sensor_module.INVERTER_SENSORS
    }
    sample_data = {
        sensor_module.KEY_BATTERY_VOLTAGE: 40.0,
        sensor_module.KEY_AC_OUTPUT_VOLTAGE: 230.0,
        sensor_module.KEY_AC_OUTPUT_CURRENT: 5.0,
        sensor_module.KEY_AC_OUTPUT_FREQUENCY: 50.0,
        sensor_module.KEY_INPUT_FREQUENCY: 50.0,
        sensor_module.KEY_LOAD_ACTIVE_POWER: 500,
        sensor_module.KEY_LOAD_APPARENT_POWER: 550,
        sensor_module.KEY_TEMPERATURE: 25.3,
        sensor_module.KEY_DEVICE_ID: 32,
        sensor_module.KEY_MODEL: "RIV1220PU-126",
    }

    assert descriptions[sensor_module.KEY_BATTERY_VOLTAGE].value_fn(sample_data) == 40.0
    assert (
        descriptions[sensor_module.KEY_AC_OUTPUT_VOLTAGE].value_fn(sample_data) == 230.0
    )
    assert (
        descriptions[sensor_module.KEY_LOAD_ACTIVE_POWER].value_fn(sample_data) == 500
    )
    assert (
        descriptions[sensor_module.KEY_MODEL].value_fn(sample_data) == "RIV1220PU-126"
    )


def test_aggregate_health_sensor_rollup() -> None:
    """Ensure aggregate health rolls up device status and lists failures."""
    sensor_module = _load_sensor_module()

    hass = MagicMock()
    hass.data = {sensor_module.DOMAIN: {}}

    coordinator_healthy = MagicMock()
    coordinator_healthy.address = "AA:BB:CC:DD:EE:01"
    coordinator_healthy.last_update_success = True
    coordinator_healthy.warn_rssi = -80
    coordinator_healthy.critical_rssi = -90
    device_healthy = MagicMock()
    device_healthy.name = "Renogy Healthy"
    device_healthy.address = coordinator_healthy.address
    device_healthy.device_type = sensor_module.DeviceType.CONTROLLER.value
    device_healthy.is_available = True
    device_healthy.rssi = -60
    coordinator_healthy.device = device_healthy

    coordinator_critical = MagicMock()
    coordinator_critical.address = "AA:BB:CC:DD:EE:02"
    coordinator_critical.last_update_success = True
    coordinator_critical.warn_rssi = -80
    coordinator_critical.critical_rssi = -90
    device_critical = MagicMock()
    device_critical.name = "Renogy Critical"
    device_critical.address = coordinator_critical.address
    device_critical.device_type = sensor_module.DeviceType.SHUNT300.value
    device_critical.is_available = True
    device_critical.rssi = -95
    coordinator_critical.device = device_critical

    hass.data[sensor_module.DOMAIN]["entry-1"] = {
        "coordinator": coordinator_healthy,
        "devices": [device_healthy],
    }
    hass.data[sensor_module.DOMAIN]["entry-2"] = {
        "coordinator": coordinator_critical,
        "devices": [device_critical],
    }

    entity = sensor_module.RenogyAggregateHealthSensor(hass)
    entity._handle_update()

    assert entity.native_value == "critical"
    attrs = entity.extra_state_attributes
    assert attrs["total_devices"] == 2
    assert attrs["critical_devices"] == 1
    assert attrs["healthy_devices"] == 1
    assert len(attrs["all_devices"]) == 2
    assert any(
        failing["name"] == "Renogy Critical" and failing["status"] == "critical"
        for failing in attrs["failing_devices"]
    )
    assert any(
        device["name"] == "Renogy Healthy" and device["status"] == "healthy"
        for device in attrs["all_devices"]
    )


def test_rssi_trend_computation() -> None:
    """Ensure RSSI trend calculations are stable/improving/declining."""
    sensor_module = _load_sensor_module()

    assert sensor_module._compute_rssi_trend([]) == "unknown"
    assert sensor_module._compute_rssi_trend([-70]) == "unknown"
    assert sensor_module._compute_rssi_trend([-70, -69, -68]) == "improving"
    assert sensor_module._compute_rssi_trend([-60, -62, -64]) == "declining"
    assert sensor_module._compute_rssi_trend([-70, -69, -70]) == "stable"


def test_rssi_trend_sensor_reads_coordinator_samples() -> None:
    """Ensure RSSI trend sensor reads from coordinator samples."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device = None
    coordinator.last_update_success = True
    coordinator._rssi_samples = [-70.0, -68.0, -65.0]

    description = next(
        item
        for item in sensor_module.HEALTH_SENSORS
        if item.key == sensor_module.KEY_RSSI_TREND
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        None,
        description,
        "Health",
        sensor_module.DeviceType.CONTROLLER.value,
    )

    assert entity.native_value == "improving"


def test_sensor_uses_device_alias_for_display_name() -> None:
    """Ensure alias overrides BLE name for entity and device info."""
    sensor_module = _load_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.device_alias = "Basement Rig"

    device = MagicMock()
    device.address = coordinator.address
    device.name = "RTMShunt300A1B2"
    device.parsed_data = {}

    description = next(
        item
        for item in sensor_module.SHUNT300_SENSORS
        if item.key == sensor_module.KEY_SHUNT_VOLTAGE
    )

    entity = sensor_module.RenogyBLESensor(
        coordinator,
        device,
        description,
        "Shunt",
        sensor_module.DeviceType.SHUNT300.value,
    )

    assert entity._attr_name.startswith("Basement Rig")
    assert entity._attr_device_info.get("name") == "Basement Rig"
