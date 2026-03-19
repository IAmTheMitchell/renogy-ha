"""Binary sensors for Renogy BLE devices."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    DEFAULT_WARN_RSSI,
    DOMAIN,
    LOGGER,
)
from .sensor import _resolve_device_display_name


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Renogy binary sensors from a config entry."""
    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    coordinator = (
        entry_data.get("coordinator") if isinstance(entry_data, dict) else None
    )
    if coordinator is None:
        LOGGER.error("Coordinator not found for Renogy BLE binary sensor setup")
        return

    device_type = entry.data.get(CONF_DEVICE_TYPE, DEFAULT_DEVICE_TYPE)
    device = coordinator.device
    if device is None:
        devices = entry_data.get("devices", []) if isinstance(entry_data, dict) else []
        if isinstance(devices, list) and devices:
            device = devices[0]

    async_add_entities(
        [RenogyLowRSSIBinarySensor(coordinator, device, device_type)], True
    )


class RenogyLowRSSIBinarySensor(PassiveBluetoothCoordinatorEntity, BinarySensorEntity):
    """Binary sensor indicating a low RSSI connection."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: RenogyActiveBluetoothCoordinator,
        device: Optional[RenogyBLEDevice],
        device_type: str,
    ) -> None:
        """Initialize the low RSSI sensor."""
        super().__init__(coordinator)
        self._device = device
        self._device_type = device_type
        self._last_updated: datetime | None = None

        display_name = _resolve_device_display_name(
            coordinator=coordinator,
            device=device,
            fallback=f"Renogy {device_type.capitalize()}",
        )
        address = (
            device.address
            if device is not None
            else getattr(coordinator, "address", "")
        )
        self._attr_unique_id = f"{address}_low_rssi"
        self._attr_name = f"{display_name} Low RSSI"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=display_name,
            manufacturer=ATTR_MANUFACTURER,
            model=f"Renogy {device_type.capitalize()}",
            hw_version=f"BLE Address: {address}",
            sw_version=device_type.capitalize(),
        )

    @property
    def device(self) -> Optional[RenogyBLEDevice]:
        """Return the associated device, if available."""
        if self._device:
            return self._device
        if hasattr(self.coordinator, "device"):
            device = cast(
                Optional[RenogyBLEDevice], getattr(self.coordinator, "device", None)
            )
            if device is not None:
                self._device = device
        return self._device

    @property
    def available(self) -> bool:
        """Return availability based on coordinator/device health."""
        last_success = getattr(self.coordinator, "last_update_success", True)
        if isinstance(last_success, bool) and not last_success:
            return False
        if self._device and hasattr(self._device, "is_available"):
            return bool(self._device.is_available)
        return True

    @property
    def is_on(self) -> bool | None:
        """Return True if RSSI is below warning threshold."""
        rssi = None
        device = self.device
        if device and isinstance(getattr(device, "rssi", None), (int, float)):
            rssi = device.rssi
        if rssi is None:
            return None

        warn_rssi = getattr(self.coordinator, "warn_rssi", DEFAULT_WARN_RSSI)
        critical_rssi = getattr(
            self.coordinator, "critical_rssi", DEFAULT_CRITICAL_RSSI
        )
        if not isinstance(warn_rssi, (int, float)):
            warn_rssi = DEFAULT_WARN_RSSI
        if not isinstance(critical_rssi, (int, float)):
            critical_rssi = DEFAULT_CRITICAL_RSSI

        return rssi <= warn_rssi or rssi <= critical_rssi

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return attributes for diagnostics."""
        attrs: dict[str, Any] = {}
        if self._last_updated:
            attrs["last_updated"] = self._last_updated.isoformat()

        device = self.device
        if device and hasattr(device, "rssi"):
            attrs["rssi"] = device.rssi

        warn_rssi = getattr(self.coordinator, "warn_rssi", DEFAULT_WARN_RSSI)
        critical_rssi = getattr(
            self.coordinator, "critical_rssi", DEFAULT_CRITICAL_RSSI
        )
        attrs["warn_rssi"] = warn_rssi
        attrs["critical_rssi"] = critical_rssi

        status = "unknown"
        rssi = attrs.get("rssi")
        if isinstance(rssi, (int, float)):
            if isinstance(critical_rssi, (int, float)) and rssi <= critical_rssi:
                status = "critical"
            elif isinstance(warn_rssi, (int, float)) and rssi <= warn_rssi:
                status = "warn"
            else:
                status = "ok"
        attrs["rssi_status"] = status
        return attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator updates."""
        if (
            not self._device
            and hasattr(self.coordinator, "device")
            and self.coordinator.device
        ):
            self._device = cast(
                RenogyBLEDevice, getattr(self.coordinator, "device", None)
            )
            address = self._device.address
            display_name = _resolve_device_display_name(
                coordinator=cast(RenogyActiveBluetoothCoordinator, self.coordinator),
                device=self._device,
                fallback=f"Renogy {self._device_type.capitalize()}",
            )
            self._attr_unique_id = f"{address}_low_rssi"
            self._attr_name = f"{display_name} Low RSSI"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, address)},
                name=display_name,
                manufacturer=ATTR_MANUFACTURER,
                model=f"Renogy {self._device_type.capitalize()}",
                hw_version=f"BLE Address: {address}",
                sw_version=self._device_type.capitalize(),
            )

        self._last_updated = datetime.now()
        self.async_write_ha_state()
