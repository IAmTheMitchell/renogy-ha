"""Tests for Communication Hub logical battery sensor entities."""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock


@dataclass(frozen=True, slots=True)
class _BatteryState:
    slave_id: int
    battery_voltage: float | None = None
    battery_current: float | None = None
    battery_power: float | None = None
    battery_remaining_capacity: float | None = None
    battery_capacity: float | None = None
    battery_percentage: float | None = None
    available: bool = True


class _Coordinator:
    def __init__(self) -> None:
        self.address = "F0:F8:F2:57:47:0D"
        self.communication_hub_enabled = True
        self.last_update_success = True
        self.device = SimpleNamespace(is_available=True)
        self.hub_batteries: tuple[_BatteryState, ...] = ()
        self.listeners: list[Any] = []

    def async_add_listener(self, callback: Any, context: Any = None) -> Any:
        del context
        self.listeners.append(callback)

        def remove_listener() -> None:
            if callback in self.listeners:
                self.listeners.remove(callback)

        return remove_listener

    def notify(self) -> None:
        for listener in tuple(self.listeners):
            listener()


class _ConfigEntry:
    def __init__(self) -> None:
        self.unload_callbacks: list[Any] = []

    def async_on_unload(self, callback: Any) -> None:
        self.unload_callbacks.append(callback)


def _install_module_stubs() -> None:
    homeassistant_module = cast(Any, types.ModuleType("homeassistant"))
    sys.modules["homeassistant"] = homeassistant_module

    components_module = cast(Any, types.ModuleType("homeassistant.components"))
    bluetooth_module = cast(Any, types.ModuleType("homeassistant.components.bluetooth"))
    passive_module = cast(
        Any,
        types.ModuleType(
            "homeassistant.components.bluetooth.passive_update_coordinator"
        ),
    )

    class PassiveBluetoothCoordinatorEntity:
        def __init__(self, coordinator: Any) -> None:
            self.coordinator = coordinator

    passive_module.PassiveBluetoothCoordinatorEntity = PassiveBluetoothCoordinatorEntity
    sys.modules["homeassistant.components"] = components_module
    sys.modules["homeassistant.components.bluetooth"] = bluetooth_module
    sys.modules["homeassistant.components.bluetooth.passive_update_coordinator"] = (
        passive_module
    )

    sensor_module = cast(Any, types.ModuleType("homeassistant.components.sensor"))

    @dataclass(frozen=True)
    class SensorEntityDescription:
        key: str
        name: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: str | None = None
        state_class: str | None = None
        suggested_display_precision: int | None = None

    class SensorEntity:
        pass

    class SensorDeviceClass:
        VOLTAGE = "voltage"
        CURRENT = "current"
        POWER = "power"
        BATTERY = "battery"

    class SensorStateClass:
        MEASUREMENT = "measurement"

    sensor_module.SensorEntity = SensorEntity
    sensor_module.SensorEntityDescription = SensorEntityDescription
    sensor_module.SensorDeviceClass = SensorDeviceClass
    sensor_module.SensorStateClass = SensorStateClass
    sys.modules["homeassistant.components.sensor"] = sensor_module

    config_entries_module = cast(Any, types.ModuleType("homeassistant.config_entries"))

    class ConfigEntry:
        pass

    config_entries_module.ConfigEntry = ConfigEntry
    sys.modules["homeassistant.config_entries"] = config_entries_module

    const_module = cast(Any, types.ModuleType("homeassistant.const"))
    const_module.PERCENTAGE = "%"

    class UnitOfElectricCurrent:
        AMPERE = "A"

    class UnitOfElectricPotential:
        VOLT = "V"

    class UnitOfPower:
        WATT = "W"

    const_module.UnitOfElectricCurrent = UnitOfElectricCurrent
    const_module.UnitOfElectricPotential = UnitOfElectricPotential
    const_module.UnitOfPower = UnitOfPower
    sys.modules["homeassistant.const"] = const_module

    core_module = cast(Any, types.ModuleType("homeassistant.core"))

    def callback(func: Any) -> Any:
        return func

    core_module.callback = callback
    sys.modules["homeassistant.core"] = core_module

    helpers_module = cast(Any, types.ModuleType("homeassistant.helpers"))
    sys.modules["homeassistant.helpers"] = helpers_module

    device_registry_module = cast(
        Any, types.ModuleType("homeassistant.helpers.device_registry")
    )

    class DeviceInfo(dict):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)

    device_registry_module.DeviceInfo = DeviceInfo
    sys.modules["homeassistant.helpers.device_registry"] = device_registry_module

    entity_platform_module = cast(
        Any, types.ModuleType("homeassistant.helpers.entity_platform")
    )

    class AddEntitiesCallback:
        pass

    entity_platform_module.AddEntitiesCallback = AddEntitiesCallback
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_module

    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg

    # hub_sensor.py can safely use the real integration constants.
    # Do not leave a synthetic custom_components.renogy.const module behind,
    # because later tests import the actual integration package.
    sys.modules.pop("custom_components.renogy.const", None)

    hub_stub = cast(Any, types.ModuleType("custom_components.renogy.hub"))
    hub_stub.RenogyHubBatteryState = _BatteryState
    hub_stub.hub_battery_identifier = lambda address, slave_id: (
        f"{address}:hub:{slave_id:02X}"
    )
    sys.modules["custom_components.renogy.hub"] = hub_stub


def _load_hub_sensor_module() -> Any:
    """Load the Hub sensor module without leaking test stubs to later tests."""
    _install_module_stubs()
    sys.modules.pop("custom_components.renogy.hub_sensor", None)

    module = importlib.import_module("custom_components.renogy.hub_sensor")

    # Hub-specific imports and the synthetic integration package are scoped to
    # these focused tests. Remove them after import so unrelated platform tests
    # load the production package and constants afresh.
    sys.modules.pop("custom_components.renogy.hub", None)
    sys.modules.pop("custom_components.renogy.const", None)
    sys.modules.pop("custom_components.renogy", None)
    custom_components_pkg = sys.modules.get("custom_components")
    if custom_components_pkg is not None:
        custom_components_pkg.__dict__.pop("renogy", None)

    return module


def test_hub_sensor_descriptions_expose_only_validated_telemetry() -> None:
    module = _load_hub_sensor_module()

    assert {description.key for description in module.HUB_BATTERY_SENSORS} == {
        "battery_voltage",
        "battery_current",
        "battery_power",
        "battery_remaining_capacity",
        "battery_capacity",
        "battery_percentage",
    }


def test_hub_sensor_setup_adds_noncontiguous_responders_once() -> None:
    module = _load_hub_sensor_module()
    coordinator = _Coordinator()
    config_entry = _ConfigEntry()
    added_batches: list[list[Any]] = []

    module.setup_hub_battery_sensors(
        config_entry,
        coordinator,
        lambda entities: added_batches.append(list(entities)),
    )

    assert added_batches == []
    assert len(coordinator.listeners) == 1
    assert len(config_entry.unload_callbacks) == 1

    coordinator.hub_batteries = (
        _BatteryState(slave_id=0x30, battery_voltage=50.5),
        _BatteryState(slave_id=0x33, battery_voltage=50.4),
    )
    coordinator.notify()

    assert len(added_batches) == 1
    assert len(added_batches[0]) == 12
    assert {entity._slave_id for entity in added_batches[0]} == {0x30, 0x33}

    coordinator.notify()
    assert len(added_batches) == 1

    coordinator.hub_batteries = (
        *coordinator.hub_batteries,
        _BatteryState(slave_id=0x31, battery_voltage=50.5),
    )
    coordinator.notify()

    assert len(added_batches) == 2
    assert len(added_batches[1]) == 6
    assert {entity._slave_id for entity in added_batches[1]} == {0x31}


def test_hub_battery_0x33_is_child_device_with_validated_values() -> None:
    module = _load_hub_sensor_module()
    coordinator = _Coordinator()
    coordinator.hub_batteries = (
        _BatteryState(
            slave_id=0x33,
            battery_voltage=50.4,
            battery_current=3.26,
            battery_power=164.304,
            battery_remaining_capacity=44.493,
            battery_capacity=49.995,
            battery_percentage=89.0,
        ),
    )

    entities = [
        module.RenogyHubBatterySensor(coordinator, 0x33, description)
        for description in module.HUB_BATTERY_SENSORS
    ]
    entities_by_key = {entity.entity_description.key: entity for entity in entities}

    assert entities_by_key["battery_voltage"].native_value == 50.4
    assert entities_by_key["battery_current"].native_value == 3.26
    assert entities_by_key["battery_power"].native_value == 164.304
    assert entities_by_key["battery_remaining_capacity"].native_value == 44.493
    assert entities_by_key["battery_capacity"].native_value == 49.995
    assert entities_by_key["battery_percentage"].native_value == 89.0

    voltage = entities_by_key["battery_voltage"]
    assert voltage.available is True
    assert voltage._attr_unique_id == "F0:F8:F2:57:47:0D:hub:33_battery_voltage"
    assert voltage._attr_device_info["identifiers"] == {
        ("renogy", "F0:F8:F2:57:47:0D:hub:33")
    }
    assert voltage._attr_device_info["via_device"] == (
        "renogy",
        "F0:F8:F2:57:47:0D",
    )
    assert voltage._attr_device_info["name"] == "Renogy Hub Battery 0x33"
    assert voltage.extra_state_attributes == {"slave_id": "0x33"}


def test_hub_battery_sensor_tracks_logical_battery_availability() -> None:
    module = _load_hub_sensor_module()
    coordinator = _Coordinator()
    coordinator.hub_batteries = (
        _BatteryState(
            slave_id=0x33,
            battery_voltage=50.4,
            available=False,
        ),
    )
    entity = module.RenogyHubBatterySensor(
        coordinator,
        0x33,
        module.HUB_BATTERY_SENSORS[0],
    )

    assert entity.available is False

    coordinator.hub_batteries = (
        _BatteryState(
            slave_id=0x33,
            battery_voltage=50.5,
            available=True,
        ),
    )
    assert entity.available is True
    assert entity.native_value == 50.5

    coordinator.last_update_success = False
    assert entity.available is True

    coordinator.device.is_available = False
    assert entity.available is False


def test_hub_sensor_setup_is_disabled_for_normal_coordinator() -> None:
    module = _load_hub_sensor_module()
    coordinator = _Coordinator()
    coordinator.communication_hub_enabled = False
    config_entry = _ConfigEntry()
    async_add_entities = MagicMock()

    module.setup_hub_battery_sensors(
        config_entry,
        coordinator,
        async_add_entities,
    )

    assert coordinator.listeners == []
    assert config_entry.unload_callbacks == []
    async_add_entities.assert_not_called()
