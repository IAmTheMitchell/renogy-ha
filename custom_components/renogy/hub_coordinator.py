"""Hub-aware coordinator extension for Renogy BLE devices."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .ble import RenogyActiveBluetoothCoordinator, RenogyBLEDevice
from .hub import RenogyHubBatteryManager, RenogyHubBatteryState

HubManagerFactory = Callable[[Any], RenogyHubBatteryManager]
HUB_REDISCOVERY_INTERVAL_SECONDS = 60 * 60


class RenogyHubBluetoothCoordinator(RenogyActiveBluetoothCoordinator):
    """Extend the normal coordinator with opt-in Hub battery polling."""

    def __init__(
        self,
        *args: Any,
        communication_hub_enabled: bool = False,
        hub_manager_factory: HubManagerFactory | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the coordinator and optional Communication Hub manager."""
        super().__init__(*args, **kwargs)
        self.communication_hub_enabled = communication_hub_enabled
        self._last_hub_discovery: float | None = None
        self._hub_battery_manager: RenogyHubBatteryManager | None = None

        if communication_hub_enabled:
            factory = hub_manager_factory or RenogyHubBatteryManager
            self._hub_battery_manager = factory(self._ble_client)

    @property
    def hub_batteries(self) -> tuple[RenogyHubBatteryState, ...]:
        """Return cached logical batteries discovered through the Hub."""
        if self._hub_battery_manager is None:
            return ()
        return self._hub_battery_manager.batteries

    async def _read_device_data(self, service_info: Any) -> bool:
        """Read the primary device, then poll Hub batteries when enabled."""
        success = await super()._read_device_data(service_info)
        if not success or self._hub_battery_manager is None or self.device is None:
            return success

        await self._async_update_hub_batteries(self.device)
        return success

    async def _async_update_hub_batteries(
        self,
        device: RenogyBLEDevice,
        *,
        rediscover: bool | None = None,
    ) -> bool:
        """Refresh Hub battery state without changing primary-device availability."""
        manager = self._hub_battery_manager
        if manager is None:
            return False

        if rediscover is None:
            now = time.monotonic()
            rediscover = (
                self._last_hub_discovery is None
                or now - self._last_hub_discovery >= HUB_REDISCOVERY_INTERVAL_SECONDS
            )

        # The parent read releases the base coordinator lock before reaching this
        # extension. Reacquire it so Hub reads cannot overlap refreshes or writes.
        async with self._connection_lock:
            self._connection_in_progress = True
            try:
                if rediscover:
                    self._last_hub_discovery = time.monotonic()
                updated = await manager.async_update(device, rediscover=rediscover)
            except Exception as err:  # noqa: BLE001
                manager.mark_unavailable(err)
                self.logger.warning(
                    "Communication Hub battery read failed for %s: %s",
                    device.address,
                    err,
                )
                return False
            finally:
                self._connection_in_progress = False

            if not updated and manager.last_error is not None:
                self.logger.debug(
                    "Communication Hub battery read returned no update for %s: %s",
                    device.address,
                    manager.last_error,
                )
            return updated

    async def async_rediscover_hub_batteries(self) -> bool:
        """Explicitly rescan the bounded Hub slave range for battery changes."""
        if self._hub_battery_manager is None or self.device is None:
            return False
        return await self._async_update_hub_batteries(self.device, rediscover=True)
