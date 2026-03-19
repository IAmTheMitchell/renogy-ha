"""Tests for Renogy BLE binary sensors."""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any, cast
from unittest.mock import MagicMock

from tests.test_sensor_setup import _install_module_stubs


def _install_binary_sensor_stubs() -> None:
    """Install binary sensor module stubs."""
    binary_sensor_module = cast(
        Any, types.ModuleType("homeassistant.components.binary_sensor")
    )

    class BinarySensorEntity:
        """Stub BinarySensorEntity for testing."""

        @property
        def name(self) -> str:
            """Return the entity name when available."""
            return getattr(self, "_attr_name", "Unknown")

        def async_write_ha_state(self) -> None:
            """Stub state write for testing."""
            return None

    class BinarySensorDeviceClass:
        """Stub binary sensor device classes."""

        PROBLEM = "problem"

    binary_sensor_module.BinarySensorEntity = BinarySensorEntity
    binary_sensor_module.BinarySensorDeviceClass = BinarySensorDeviceClass
    sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_module


def _load_binary_sensor_module() -> Any:
    """Load binary_sensor module with HA stubs."""
    _install_module_stubs()
    _install_binary_sensor_stubs()
    sys.modules.pop("custom_components.renogy.binary_sensor", None)
    return importlib.import_module("custom_components.renogy.binary_sensor")


def test_low_rssi_binary_sensor_on_when_below_warn() -> None:
    """Ensure low RSSI sensor turns on at/below warn threshold."""
    module = _load_binary_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "BT-TH-TEST"
    device.is_available = True
    device.rssi = -85

    entity = module.RenogyLowRSSIBinarySensor(coordinator, device, "controller")

    assert entity.is_on is True
    assert entity.extra_state_attributes["rssi_status"] == "warn"


def test_low_rssi_binary_sensor_off_when_ok() -> None:
    """Ensure low RSSI sensor turns off when RSSI is healthy."""
    module = _load_binary_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "BT-TH-TEST"
    device.is_available = True
    device.rssi = -60

    entity = module.RenogyLowRSSIBinarySensor(coordinator, device, "controller")

    assert entity.is_on is False
    assert entity.extra_state_attributes["rssi_status"] == "ok"


def test_low_rssi_binary_sensor_unknown_when_no_rssi() -> None:
    """Ensure low RSSI sensor reports unknown when RSSI is missing."""
    module = _load_binary_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "BT-TH-TEST"
    device.is_available = True
    device.rssi = None

    entity = module.RenogyLowRSSIBinarySensor(coordinator, device, "controller")

    assert entity.is_on is None
    assert entity.extra_state_attributes["rssi_status"] == "unknown"


def test_low_rssi_sensor_uses_alias_name() -> None:
    """Ensure alias overrides device name in entity naming."""
    module = _load_binary_sensor_module()

    coordinator = MagicMock()
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.last_update_success = True
    coordinator.warn_rssi = -80
    coordinator.critical_rssi = -90
    coordinator.device_alias = "Basement Renogy"

    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "BT-TH-TEST"
    device.is_available = True
    device.rssi = -60

    entity = module.RenogyLowRSSIBinarySensor(coordinator, device, "controller")

    assert entity.name == "Basement Renogy Low RSSI"
