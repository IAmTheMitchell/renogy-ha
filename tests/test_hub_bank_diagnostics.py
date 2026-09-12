"""Tests for Communication Hub communicating-bank imbalance diagnostics."""

from __future__ import annotations

import asyncio
import importlib
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


@dataclass
class _FakeResult:
    success: bool
    batteries: list[Any]
    error: Exception | None = None


class _FakeHub:
    def __init__(self, results: list[_FakeResult]) -> None:
        self._results = list(results)

    async def read_batteries(
        self,
        _device: Any,
        *,
        rediscover: bool = False,
    ) -> _FakeResult:
        del rediscover
        return self._results.pop(0)


def _battery(slave_id: int, **data: Any) -> Any:
    return SimpleNamespace(slave_id=slave_id, parsed_data=data)


def _install_integration_package() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg


def _load_hub_module() -> Any:
    _install_integration_package()
    sys.modules.pop("custom_components.renogy.hub", None)
    return importlib.import_module("custom_components.renogy.hub")


def _manager(module: Any, results: list[_FakeResult]) -> Any:
    fake_hub = _FakeHub(results)
    return module.RenogyHubBatteryManager(
        object(),
        hub_factory=lambda _client: fake_hub,
    )


def test_hub_bank_builds_imbalance_diagnostics_from_hardware_values() -> None:
    module = _load_hub_module()
    manager = _manager(
        module,
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
        ],
    )

    assert asyncio.run(manager.async_update(object())) is True
    bank = manager.bank
    assert bank is not None

    assert bank.battery_percentage_min == 91.4
    assert bank.battery_percentage_min_slave_id == 0x30
    assert bank.battery_percentage_max == 96.6
    assert bank.battery_percentage_max_slave_id == 0x33
    assert bank.battery_percentage_spread == 5.2

    assert bank.battery_voltage_min == 49.6
    assert bank.battery_voltage_min_slave_id == 0x30
    assert bank.battery_voltage_max == 49.7
    assert bank.battery_voltage_max_slave_id == 0x31
    assert bank.battery_voltage_spread == 0.1

    assert bank.battery_current_spread == 2.05


def test_hub_bank_diagnostics_exclude_unavailable_batteries() -> None:
    module = _load_hub_module()
    manager = _manager(
        module,
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=50.1,
                        battery_current=1.2,
                        battery_percentage=88.0,
                    ),
                    _battery(
                        0x31,
                        battery_voltage=50.3,
                        battery_current=2.0,
                        battery_percentage=92.0,
                    ),
                ],
            ),
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=50.2,
                        battery_current=1.4,
                        battery_percentage=89.0,
                    )
                ],
                TimeoutError("battery timeout"),
            ),
        ],
    )

    async def _run() -> None:
        assert await manager.async_update(object()) is True
        assert await manager.async_update(object()) is True

    asyncio.run(_run())

    bank = manager.bank
    assert bank is not None
    assert bank.communicating_battery_count == 1
    assert bank.discovered_battery_count == 2
    assert bank.battery_percentage_min == 89.0
    assert bank.battery_percentage_max == 89.0
    assert bank.battery_percentage_spread == 0.0
    assert bank.battery_percentage_min_slave_id == 0x30
    assert bank.battery_percentage_max_slave_id == 0x30
    assert bank.battery_voltage_spread == 0.0
    assert bank.battery_current_spread == 0.0


def test_hub_bank_diagnostics_require_complete_communicating_fields() -> None:
    module = _load_hub_module()
    manager = _manager(
        module,
        [
            _FakeResult(
                True,
                [
                    _battery(
                        0x30,
                        battery_voltage=50.1,
                        battery_current=1.2,
                        battery_percentage=88.0,
                    ),
                    _battery(
                        0x31,
                        battery_voltage=None,
                        battery_current=None,
                        battery_percentage=None,
                    ),
                ],
            )
        ],
    )

    asyncio.run(manager.async_update(object()))
    bank = manager.bank
    assert bank is not None
    assert bank.battery_percentage_min is None
    assert bank.battery_percentage_max is None
    assert bank.battery_percentage_spread is None
    assert bank.battery_percentage_min_slave_id is None
    assert bank.battery_percentage_max_slave_id is None
    assert bank.battery_voltage_min is None
    assert bank.battery_voltage_max is None
    assert bank.battery_voltage_spread is None
    assert bank.battery_current_spread is None
