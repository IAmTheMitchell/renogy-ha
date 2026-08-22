"""Tests for opt-in Communication Hub coordinator behavior."""

from __future__ import annotations

import asyncio
import importlib
import sys
import time
import types
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock


def _load_hub_coordinator_module() -> Any:
    """Load hub_coordinator.py with isolated integration dependencies."""
    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg

    ble_module = cast(Any, types.ModuleType("custom_components.renogy.ble"))

    class RenogyBLEDevice:
        """Minimal logical BLE device used by coordinator tests."""

        def __init__(self, address: str = "AA:BB:CC:DD:EE:FF") -> None:
            self.address = address

    class RenogyActiveBluetoothCoordinator:
        """Minimal base coordinator exposing primary-read behavior."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._ble_client = object()
            self._connection_lock = asyncio.Lock()
            self._connection_in_progress = False
            self.device = RenogyBLEDevice(kwargs.get("address", "AA:BB:CC:DD:EE:FF"))
            self.logger = MagicMock()
            self.last_update_success = True
            self.primary_success = True

        async def _read_device_data(self, _service_info: Any) -> bool:
            self.last_update_success = self.primary_success
            return self.primary_success

    ble_module.RenogyBLEDevice = RenogyBLEDevice
    ble_module.RenogyActiveBluetoothCoordinator = RenogyActiveBluetoothCoordinator
    sys.modules["custom_components.renogy.ble"] = ble_module

    hub_module = cast(Any, types.ModuleType("custom_components.renogy.hub"))

    class RenogyHubBatteryState:
        """Minimal cached Hub state placeholder."""

    class RenogyHubBatteryManager:
        """Default manager placeholder; tests inject a fake manager factory."""

        def __init__(self, _client: Any) -> None:
            raise AssertionError("Tests should inject a Hub manager factory")

    hub_module.RenogyHubBatteryState = RenogyHubBatteryState
    hub_module.RenogyHubBatteryManager = RenogyHubBatteryManager
    sys.modules["custom_components.renogy.hub"] = hub_module

    sys.modules.pop("custom_components.renogy.hub_coordinator", None)
    return importlib.import_module("custom_components.renogy.hub_coordinator")


class _FakeHubManager:
    """Record coordinator Hub update requests."""

    def __init__(
        self,
        *,
        results: list[bool] | None = None,
        error: Exception | None = None,
        batteries: tuple[Any, ...] = (),
    ) -> None:
        self._results = list(results or [True])
        self._error = error
        self.batteries = batteries
        self.last_error: Exception | None = None
        self.calls: list[bool] = []
        self.unavailable_errors: list[Exception] = []

    def mark_unavailable(self, error: Exception) -> None:
        """Record invalidation of cached Hub battery state."""
        self.last_error = error
        self.unavailable_errors.append(error)

    async def async_update(self, _device: Any, *, rediscover: bool = False) -> bool:
        self.calls.append(rediscover)
        if self._error is not None:
            raise self._error
        result = self._results.pop(0)
        if not result:
            self.last_error = RuntimeError("Hub returned no battery update")
        return result


def _coordinator(module: Any, manager: _FakeHubManager, *, enabled: bool = True) -> Any:
    """Create a Hub-aware coordinator using the supplied fake manager."""
    return module.RenogyHubBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        communication_hub_enabled=enabled,
        hub_manager_factory=lambda _client: manager,
    )


def test_hub_coordinator_is_disabled_by_default() -> None:
    """Default coordinator behavior must not create or poll a Hub manager."""
    module = _load_hub_coordinator_module()
    coordinator = module.RenogyHubBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
    )

    assert coordinator.communication_hub_enabled is False
    assert coordinator.hub_batteries == ()
    assert asyncio.run(coordinator._read_device_data(object())) is True


def test_hub_coordinator_discovers_once_then_uses_cached_polling() -> None:
    """First Hub read should rediscover, while later reads use cached slaves."""
    module = _load_hub_coordinator_module()
    manager = _FakeHubManager(results=[True, True])
    coordinator = _coordinator(module, manager)

    async def _run() -> None:
        assert await coordinator._read_device_data(object()) is True
        assert await coordinator._read_device_data(object()) is True

    asyncio.run(_run())

    assert manager.calls == [True, False]


def test_hub_coordinator_skips_hub_when_primary_read_fails() -> None:
    """A failed primary device read must not start a Hub battery transaction."""
    module = _load_hub_coordinator_module()
    manager = _FakeHubManager()
    coordinator = _coordinator(module, manager)
    coordinator.primary_success = False

    assert asyncio.run(coordinator._read_device_data(object())) is False
    assert manager.calls == []
    assert coordinator.last_update_success is False


def test_hub_failure_does_not_mark_primary_device_unavailable() -> None:
    """Hub read exceptions must not turn a successful inverter poll into failure."""
    module = _load_hub_coordinator_module()
    manager = _FakeHubManager(error=RuntimeError("Hub timeout"))
    coordinator = _coordinator(module, manager)

    assert asyncio.run(coordinator._read_device_data(object())) is True

    assert coordinator.last_update_success is True
    assert manager.calls == [True]
    assert manager.unavailable_errors == [manager._error]
    coordinator.logger.warning.assert_called_once()


def test_hub_coordinator_supports_explicit_rediscovery() -> None:
    """Explicit rediscovery should force a new bounded Hub slave scan."""
    module = _load_hub_coordinator_module()
    manager = _FakeHubManager(results=[True, True])
    coordinator = _coordinator(module, manager)

    async def _run() -> None:
        assert await coordinator._read_device_data(object()) is True
        assert await coordinator.async_rediscover_hub_batteries() is True

    asyncio.run(_run())

    assert manager.calls == [True, True]


def test_hub_coordinator_periodically_rediscovers_batteries() -> None:
    """A later poll should rescan for batteries missed during initial discovery."""
    module = _load_hub_coordinator_module()
    manager = _FakeHubManager(results=[True, True, True])
    coordinator = _coordinator(module, manager)

    async def _run() -> None:
        assert await coordinator._read_device_data(object()) is True
        assert await coordinator._read_device_data(object()) is True
        coordinator._last_hub_discovery = (
            time.monotonic() - module.HUB_REDISCOVERY_INTERVAL_SECONDS
        )
        assert await coordinator._read_device_data(object()) is True

    asyncio.run(_run())

    assert manager.calls == [True, False, True]


def test_hub_transaction_holds_coordinator_connection_guard() -> None:
    """Hub I/O should remain serialized with parent refreshes and writes."""
    module = _load_hub_coordinator_module()

    class GuardCheckingManager(_FakeHubManager):
        async def async_update(self, _device: Any, *, rediscover: bool = False) -> bool:
            assert coordinator._connection_lock.locked()
            assert coordinator._connection_in_progress is True
            return await super().async_update(_device, rediscover=rediscover)

    manager = GuardCheckingManager()
    coordinator = _coordinator(module, manager)

    assert asyncio.run(coordinator._read_device_data(object())) is True
    assert coordinator._connection_lock.locked() is False
    assert coordinator._connection_in_progress is False
