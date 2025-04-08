"""Support for Renogy BLE sensors."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    RENOGY_BT_PREFIX,
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
        value_fn=lambda data: data.get(KEY_POWER_GENERATION_TOTAL),
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

# All sensors combined
ALL_SENSORS = BATTERY_SENSORS + PV_SENSORS + LOAD_SENSORS + CONTROLLER_SENSORS


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE sensors."""
    LOGGER.debug(f"Setting up Renogy BLE sensors for entry: {config_entry.entry_id}")

    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    # Get device type from config
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
    LOGGER.debug(f"Setting up sensors for device type: {device_type}")

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
                LOGGER.debug(f"Real device name found: {coordinator.device.name}")
                real_name_found = True
                break

        if not real_name_found:
            LOGGER.debug(
                "No real device name found after waiting. Using generic name for entities."
            )

    # Now create entities with the best name we have
    if coordinator.device and (
        coordinator.device.name.startswith(RENOGY_BT_PREFIX)
        or not coordinator.device.name.startswith("Unknown")
    ):
        LOGGER.info(f"Creating entities with device name: {coordinator.device.name}")
        device_entities = create_device_entities(
            coordinator, coordinator.device, device_type
        )
    else:
        LOGGER.info("Creating entities with coordinator only (generic name)")
        device_entities = create_coordinator_entities(coordinator, device_type)

    # Add all entities to Home Assistant
    if device_entities:
        LOGGER.debug(f"Adding {len(device_entities)} entities")
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

    # Group sensors by category
    for category_name, sensor_list in {
        "Battery": BATTERY_SENSORS,
        "PV": PV_SENSORS,
        "Load": LOAD_SENSORS,
        "Controller": CONTROLLER_SENSORS,
    }.items():
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
    LOGGER.info(f"Created {len(entities)} entities with coordinator only")
    return entities


def create_device_entities(
    coordinator: RenogyActiveBluetoothCoordinator,
    device: RenogyBLEDevice,
    device_type: str = DEFAULT_DEVICE_TYPE,
) -> List[RenogyBLESensor]:
    """Create sensor entities for a device."""
    entities = create_entities_helper(coordinator, device, device_type)
    LOGGER.info(f"Created {len(entities)} entities for device {device.name}")
    return entities


class RenogyBLESensor(CoordinatorEntity, SensorEntity):
    """Representation of a Renogy BLE sensor."""

    entity_description: RenogyBLESensorDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        description: RenogyBLESensorDescription,
        category: str = None,
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
                sw_version=device_type.capitalize(),  # Add device type as software version for clarity
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
                sw_version=device_type.capitalize(),  # Add device type as software version for clarity
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
                sw_version=self._device_type.capitalize(),  # Add device type as software version
            )
            LOGGER.debug(f"Updated device info with real name: {self._device.name}")

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

        # For the actual data, check either the device's parsed_data or coordinator's data
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
                                    f"Value {value} out of reasonable range for {self.name}"
                                )
                                return None
                        except (ValueError, TypeError):
                            LOGGER.warning(
                                f"Invalid numeric value for {self.name}: {value}"
                            )
                            return None

                # Cache the value
                self._attr_native_value = value
                return value
        except Exception as e:
            LOGGER.warning(f"Error getting native value for {self.name}: {e}")
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug(f"Coordinator update for {self.name}")

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
