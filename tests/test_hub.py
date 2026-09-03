"""Tests for Communication Hub logical battery state management."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_hub_module() -> Any:
    """Load hub.py without executing the integration package initializer."""
    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg

    sys.modules.pop("custom_components.renogy.hub", None)
    return importlib.import_module("custom_components.renogy.hub")


hub_module = _load_hub_module()
RenogyHubBatteryManager = hub_module.RenogyHubBatteryManager
hub_bank_identifier = hub_module.hub_bank_identifier
hub_battery_identifier = hub_module.hub_battery_identifier


@dataclass
class _FakeResult:
    success: bool
    batteries: list[Any]
    error: Exception | None = None


class _FakeHub:
    def __init__(self, results: list[_FakeResult]) -> None:
        self._results = list(results)
        self.calls: list[bool] = []

    async def read_batteries(
        self,
        _device: Any,
        *,
        rediscover: bool = False,
    ) -> _FakeResult:
        self.calls.append(rediscover)
        return self._results.pop(0)


def _battery(slave_id: int, **data: Any) -> Any:
    return SimpleNamespace(slave_id=slave_id, parsed_data=data)


def _manager(results: list[_FakeResult]) -> tuple[Any, _FakeHub]:
    fake_hub = _FakeHub(results)
    manager = RenogyHubBatteryManager(
        object(),
        hub_factory=lambda _client: fake_hub,
    )
    return manager, fake_hub


def test_hub_manager_caches_validated_fields() -> None:
    """Validated Hub telemetry should enter Home Assistant state."""
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=49.8,
                        battery_remaining_capacity=42.389,
                        battery_capacity=49.995,
                        battery_percentage=84.8,
                        battery_current=3.26,
                        battery_power=162.348,
                    )
                ],
            )
        ]
    )

    assert asyncio.run(manager.async_update(object())) is True

    battery = manager.get_battery(0x30)
    assert battery is not None
    assert battery.available is True
    assert battery.as_dict() == {
        "slave_id": 0x30,
        "battery_voltage": 49.8,
        "battery_current": 3.26,
        "battery_power": 162.348,
        "battery_remaining_capacity": 42.389,
        "battery_capacity": 49.995,
        "battery_percentage": 84.8,
    }


def test_hub_manager_builds_communicating_bank_aggregates() -> None:
    """Bank telemetry should aggregate all currently communicating batteries."""
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=49.6,
                        battery_current=-2.87,
                        battery_power=-142.352,
                        battery_remaining_capacity=45.695,
                        battery_capacity=49.993,
                        battery_percentage=91.4,
                    ),
                    _battery(
                        0x31,
                        battery_voltage=49.7,
                        battery_current=-1.53,
                        battery_power=-76.041,
                        battery_remaining_capacity=47.494,
                        battery_capacity=49.993,
                        battery_percentage=95.0,
                    ),
                    _battery(
                        0x32,
                        battery_voltage=49.7,
                        battery_current=-1.87,
                        battery_power=-92.939,
                        battery_remaining_capacity=46.818,
                        battery_capacity=49.993,
                        battery_percentage=93.6,
                    ),
                    _battery(
                        0x33,
                        battery_voltage=49.7,
                        battery_current=-0.82,
                        battery_power=-40.754,
                        battery_remaining_capacity=48.277,
                        battery_capacity=49.995,
                        battery_percentage=96.6,
                    ),
                ],
            )
        ]
    )

    assert asyncio.run(manager.async_update(object())) is True

    bank = manager.bank
    assert bank is not None
    assert bank.as_dict() == {
        "communicating_battery_count": 4,
        "discovered_battery_count": 4,
        "battery_current": -7.09,
        "battery_power": -352.086,
        "battery_remaining_capacity": 188.284,
        "battery_capacity": 199.974,
        "battery_percentage": 94.2,
    }


def test_hub_manager_excludes_unavailable_battery_from_bank() -> None:
    """A missed battery should remain discovered but leave bank aggregates."""
    timeout_error = TimeoutError("battery timeout")
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_current=-2.0,
                        battery_power=-100.0,
                        battery_remaining_capacity=40.0,
                        battery_capacity=50.0,
                    ),
                    _battery(
                        0x31,
                        battery_current=-1.0,
                        battery_power=-50.0,
                        battery_remaining_capacity=45.0,
                        battery_capacity=50.0,
                    ),
                ],
            ),
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_current=-2.2,
                        battery_power=-110.0,
                        battery_remaining_capacity=39.0,
                        battery_capacity=50.0,
                    )
                ],
                timeout_error,
            ),
        ]
    )

    async def _run() -> None:
        assert await manager.async_update(object()) is True
        assert await manager.async_update(object()) is True

    asyncio.run(_run())

    bank = manager.bank
    assert bank is not None
    assert bank.as_dict() == {
        "communicating_battery_count": 1,
        "discovered_battery_count": 2,
        "battery_current": -2.2,
        "battery_power": -110.0,
        "battery_remaining_capacity": 39.0,
        "battery_capacity": 50.0,
        "battery_percentage": 78.0,
    }


def test_hub_manager_requires_complete_fields_for_each_bank_metric() -> None:
    """A missing value on a communicating battery must not yield a partial total."""
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_current=-2.0,
                        battery_power=-100.0,
                        battery_remaining_capacity=40.0,
                        battery_capacity=50.0,
                    ),
                    _battery(
                        0x31,
                        battery_current=None,
                        battery_power=-50.0,
                        battery_remaining_capacity=45.0,
                        battery_capacity=50.0,
                    ),
                ],
            )
        ]
    )

    asyncio.run(manager.async_update(object()))

    bank = manager.bank
    assert bank is not None
    assert bank.communicating_battery_count == 2
    assert bank.discovered_battery_count == 2
    assert bank.battery_current is None
    assert bank.battery_power == -150.0
    assert bank.battery_remaining_capacity == 85.0
    assert bank.battery_capacity == 100.0
    assert bank.battery_percentage == 85.0


def test_hub_manager_marks_missing_cached_battery_unavailable() -> None:
    """A missed cached slave should retain its last values but become unavailable."""
    timeout_error = TimeoutError("battery timeout")
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(0x30, battery_voltage=49.8, battery_percentage=84.8),
                    _battery(0x31, battery_voltage=49.8, battery_percentage=91.9),
                ],
            ),
            _FakeResult(
                True,
                [_battery(0x30, battery_voltage=49.7, battery_percentage=84.6)],
                timeout_error,
            ),
        ]
    )

    async def _run() -> None:
        assert await manager.async_update(object()) is True
        assert await manager.async_update(object()) is True

    asyncio.run(_run())

    battery_30 = manager.get_battery(0x30)
    battery_31 = manager.get_battery(0x31)
    assert battery_30 is not None and battery_30.available is True
    assert battery_30.battery_voltage == 49.7
    assert battery_31 is not None and battery_31.available is False
    assert battery_31.battery_percentage == 91.9
    assert manager.last_error is timeout_error


def test_hub_manager_rediscovery_adds_new_slave() -> None:
    """Explicit rediscovery should add newly responding logical batteries."""
    manager, fake_hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(0x30, battery_voltage=49.8),
                    _battery(0x31, battery_voltage=49.8),
                ],
            ),
            _FakeResult(
                True,
                [
                    _battery(0x30, battery_voltage=49.8),
                    _battery(0x31, battery_voltage=49.8),
                    _battery(0x32, battery_voltage=49.8),
                ],
            ),
        ]
    )

    async def _run() -> None:
        assert await manager.async_update(object()) is True
        assert await manager.async_update(object(), rediscover=True) is True

    asyncio.run(_run())

    assert fake_hub.calls == [False, True]
    assert [battery.slave_id for battery in manager.batteries] == [0x30, 0x31, 0x32]


def test_hub_manager_handles_non_numeric_optional_values() -> None:
    """Malformed optional telemetry should be ignored rather than propagated."""
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage="49.8",
                        battery_remaining_capacity="bad",
                        battery_capacity=None,
                        battery_percentage="84.8",
                    )
                ],
            )
        ]
    )

    asyncio.run(manager.async_update(object()))

    battery = manager.get_battery(0x30)
    assert battery is not None
    assert battery.battery_voltage == 49.8
    assert battery.battery_remaining_capacity is None
    assert battery.battery_capacity is None
    assert battery.battery_percentage == 84.8


def test_hub_manager_marks_all_cached_batteries_unavailable() -> None:
    """A raised Hub transaction should invalidate every cached child battery."""
    manager, _hub = _manager(
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=49.8,
                        battery_current=-2.0,
                        battery_power=-100.0,
                        battery_remaining_capacity=40.0,
                        battery_capacity=50.0,
                    ),
                    _battery(
                        0x31,
                        battery_voltage=49.7,
                        battery_current=-1.0,
                        battery_power=-50.0,
                        battery_remaining_capacity=45.0,
                        battery_capacity=50.0,
                    ),
                ],
            )
        ]
    )
    asyncio.run(manager.async_update(object()))
    error = TimeoutError("Hub connection failed")

    manager.mark_unavailable(error)

    assert manager.last_error is error
    assert all(not battery.available for battery in manager.batteries)
    bank = manager.bank
    assert bank is not None
    assert bank.communicating_battery_count == 0
    assert bank.discovered_battery_count == 2
    assert bank.battery_current is None
    assert bank.battery_power is None
    assert bank.battery_remaining_capacity is None
    assert bank.battery_capacity is None
    assert bank.battery_percentage is None


def test_hub_manager_has_no_bank_before_any_battery_is_discovered() -> None:
    """The logical bank should not exist until at least one battery is discovered."""
    manager, _hub = _manager([])

    assert manager.bank is None


def test_hub_battery_identifier_is_stable_and_slave_specific() -> None:
    """Logical battery identifiers should be unique beneath one BLE address."""
    address = "F0:F8:F2:57:47:0D"

    assert hub_battery_identifier(address, 0x30) == "F0:F8:F2:57:47:0D:hub:30"
    assert hub_battery_identifier(address, 0x31) == "F0:F8:F2:57:47:0D:hub:31"


def test_hub_bank_identifier_is_stable() -> None:
    """The communicating bank should have one stable logical device identifier."""
    assert hub_bank_identifier("F0:F8:F2:57:47:0D") == "F0:F8:F2:57:47:0D:hub:bank"
