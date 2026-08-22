"""Shared availability logic for Renogy entities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class CoordinatorAvailability(Protocol):
    """Coordinator fields used to determine entity availability."""

    @property
    def device(self) -> DeviceAvailability | None:
        """Return the coordinator's current device."""

    @property
    def data(self) -> Mapping[str, Any] | None:
        """Return the coordinator's cached data."""


class DeviceAvailability(Protocol):
    """Device fields used to determine entity availability."""

    @property
    def parsed_data(self) -> Mapping[str, Any]:
        """Return the device's cached parsed data."""

    @property
    def is_available(self) -> bool:
        """Return whether the device is within its failure grace."""


def is_entity_available(
    coordinator: CoordinatorAvailability,
    device: DeviceAvailability | None,
) -> bool:
    """Return whether an entity has available cached data within device grace."""
    current_device = coordinator.device or device
    if current_device is not None:
        if not current_device.is_available:
            return False
        if current_device.parsed_data:
            return True

    return bool(coordinator.data)
