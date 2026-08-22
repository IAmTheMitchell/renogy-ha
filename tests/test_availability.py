"""Tests for shared Renogy entity availability logic."""

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, cast

import pytest


def _load_availability_module() -> ModuleType:
    """Load the standalone helper without importing the integration package."""
    path = (
        Path(__file__).parents[1] / "custom_components" / "renogy" / "availability.py"
    )
    spec = importlib.util.spec_from_file_location("renogy_availability", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


is_entity_available = _load_availability_module().is_entity_available


@pytest.mark.parametrize(
    ("device", "coordinator_device", "coordinator_data", "expected"),
    [
        (None, None, None, False),
        (None, None, {"battery_voltage": 12.6}, True),
        (
            SimpleNamespace(is_available=True, parsed_data={"battery_voltage": 12.6}),
            None,
            None,
            True,
        ),
        (
            SimpleNamespace(is_available=True, parsed_data={}),
            None,
            {"battery_voltage": 12.6},
            True,
        ),
        (
            None,
            SimpleNamespace(is_available=False, parsed_data={"battery_voltage": 12.6}),
            {"battery_voltage": 12.6},
            False,
        ),
        (
            SimpleNamespace(is_available=True, parsed_data={"stale": True}),
            SimpleNamespace(is_available=False, parsed_data={"battery_voltage": 12.6}),
            {"battery_voltage": 12.6},
            False,
        ),
    ],
)
def test_entity_availability(
    device: SimpleNamespace | None,
    coordinator_device: SimpleNamespace | None,
    coordinator_data: dict[str, Any] | None,
    expected: bool,
) -> None:
    """Availability requires cached data and an available resolved device."""
    coordinator = SimpleNamespace(data=coordinator_data, device=coordinator_device)

    assert is_entity_available(cast(Any, coordinator), cast(Any, device)) is expected
