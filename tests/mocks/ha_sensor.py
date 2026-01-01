"""Mock implementations of Home Assistant sensor classes for testing."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class SensorDeviceClass(str, Enum):
    """Device class for sensors in Home Assistant."""

    BATTERY = "battery"
    CURRENT = "current"
    ENERGY = "energy"
    POWER = "power"
    TEMPERATURE = "temperature"
    VOLTAGE = "voltage"


class SensorStateClass(str, Enum):
    """State class for sensors in Home Assistant."""

    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"


class EntityCategory(str, Enum):
    """Categories for entities in Home Assistant."""

    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


@dataclass
class SensorEntityDescription:
    """Description class for sensor entities."""

    key: str
    name: Optional[str] = None
    device_class: Optional[str] = None
    state_class: Optional[str] = None
    native_unit_of_measurement: Optional[str] = None
    entity_category: Optional[str] = None
    native_value: Any = None
    value_fn: Optional[Callable] = None


class SensorEntity:
    """Base class for sensor entities."""

    def __init__(self):
        """Initialize the sensor entity."""
        self._attr_native_value = None
        self.entity_description = None
        self.available = True

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._attr_native_value
