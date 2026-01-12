"""Support for Renogy BLE switches."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .const import (
    ATTR_MANUFACTURER,
    CONF_DEVICE_TYPE,
    DEFAULT_DEVICE_TYPE,
    DOMAIN,
    LOGGER,
    RENOGY_BT_PREFIX,
)

KEY_LOAD_STATUS = "load_status"


@dataclass
class RenogyBLESwitchDescription(SwitchEntityDescription):
    """Describes a Renogy BLE switch."""


LOAD_SWITCH = RenogyBLESwitchDescription(
    key=KEY_LOAD_STATUS,
    name="DC Load",
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Renogy BLE switches."""
    LOGGER.debug("Setting up Renogy BLE switches for entry: %s", config_entry.entry_id)

    renogy_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = renogy_data["coordinator"]

    device_type = config_entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
    LOGGER.debug("Setting up switches for device type: %s", device_type)

    if (
        not coordinator.device
        or coordinator.device.name.startswith("Unknown")
        or not coordinator.device.name.startswith(RENOGY_BT_PREFIX)
    ):
        LOGGER.debug("Waiting for real device name before creating switches...")
        await coordinator.async_request_refresh()

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

    device = coordinator.device if coordinator.device else None
    async_add_entities([RenogyLoadSwitch(coordinator, device, device_type)])


class RenogyLoadSwitch(PassiveBluetoothCoordinatorEntity, SwitchEntity):
    """Representation of a Renogy DC load switch."""

    entity_description: RenogyBLESwitchDescription
    coordinator: RenogyActiveBluetoothCoordinator

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        device_type: str = DEFAULT_DEVICE_TYPE,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = LOAD_SWITCH
        self._device = device
        self._device_type = device_type
        self._attr_is_on = None

        device_model = f"Renogy {device_type.capitalize()}"
        if device and device.parsed_data and "model" in device.parsed_data:
            device_model = device.parsed_data["model"]

        if device:
            self._attr_unique_id = f"{device.address}_{self.entity_description.key}"
            self._attr_name = f"{device.name} {self.entity_description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, device.address)},
                name=device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {device.address}",
                sw_version=device_type.capitalize(),
            )
        else:
            self._attr_unique_id = (
                f"{coordinator.address}_{self.entity_description.key}"
            )
            self._attr_name = f"Renogy {self.entity_description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, coordinator.address)},
                name=f"Renogy {device_type.capitalize()}",
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {coordinator.address}",
                sw_version=device_type.capitalize(),
            )

    @property
    def device(self) -> Optional[RenogyBLEDevice]:
        """Get the current device - either stored or from coordinator."""
        if self._device:
            return self._device

        if hasattr(self.coordinator, "device") and self.coordinator.device:
            self._device = self.coordinator.device

            device_model = f"Renogy {self._device_type.capitalize()}"
            if self._device.parsed_data and "model" in self._device.parsed_data:
                device_model = self._device.parsed_data["model"]

            self._attr_unique_id = (
                f"{self._device.address}_{self.entity_description.key}"
            )
            self._attr_name = f"{self._device.name} {self.entity_description.name}"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, self._device.address)},
                name=self._device.name,
                manufacturer=ATTR_MANUFACTURER,
                model=device_model,
                hw_version=f"BLE Address: {self._device.address}",
                sw_version=self._device_type.capitalize(),
            )
            LOGGER.debug("Updated device info with real name: %s", self._device.name)

        return self._device

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        if not self.coordinator.last_update_success:
            return False

        if self._device and not self._device.is_available:
            return False

        if self._device and self._device.parsed_data:
            return True

        return bool(self.coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return True if the load is on."""
        value = self._get_load_status()
        if value is None:
            return None
        if isinstance(value, str):
            return value.lower() == "on"
        return bool(value)

    def _get_load_status(self) -> Any:
        device = self.device
        if device and device.parsed_data and KEY_LOAD_STATUS in device.parsed_data:
            return device.parsed_data.get(KEY_LOAD_STATUS)
        if isinstance(self.coordinator.data, dict):
            return self.coordinator.data.get(KEY_LOAD_STATUS)
        return None

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the load on."""
        await self._async_set_state(True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the load off."""
        await self._async_set_state(False)

    async def _async_set_state(self, state: bool) -> None:
        """Set load state and refresh entity state."""
        success = await self.coordinator.async_set_load_state(state)
        if success:
            self._attr_is_on = state
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.device
        self._attr_is_on = None
        self.async_write_ha_state()
