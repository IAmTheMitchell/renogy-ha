"""Tests for shared Renogy BLE device name helpers."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from typing import Any


def _load_device_name_module() -> Any:
    """Load device_name module without importing integration __init__."""
    repo_root = Path(__file__).resolve().parents[1]
    custom_components_path = str(repo_root / "custom_components")
    renogy_path = str(repo_root / "custom_components" / "renogy")

    custom_components_pkg = types.ModuleType("custom_components")
    custom_components_pkg.__path__ = [custom_components_path]
    sys.modules["custom_components"] = custom_components_pkg

    renogy_pkg = types.ModuleType("custom_components.renogy")
    renogy_pkg.__path__ = [renogy_path]
    sys.modules["custom_components.renogy"] = renogy_pkg

    sys.modules.pop("custom_components.renogy.const", None)
    sys.modules.pop("custom_components.renogy.device_name", None)
    return importlib.import_module("custom_components.renogy.device_name")


def test_supported_renogy_name_prefixes() -> None:
    """Supported device names should match known BLE prefixes."""
    device_name_module = _load_device_name_module()

    assert device_name_module.is_supported_renogy_ble_name("BT-TH-123456")
    assert device_name_module.is_supported_renogy_ble_name(
        f"{device_name_module.SHUNT300_BT_PREFIX}A1B2"
    )
    assert not device_name_module.is_supported_renogy_ble_name("Unknown Renogy Device")
    assert not device_name_module.is_supported_renogy_ble_name("OtherDevice")


def test_detect_device_type_from_ble_name() -> None:
    """Device type detection should infer shunt names and fallback otherwise."""
    device_name_module = _load_device_name_module()
    const_module = importlib.import_module("custom_components.renogy.const")

    assert (
        device_name_module.detect_device_type_from_ble_name("RTMShunt300A1B2")
        == const_module.DeviceType.SHUNT300.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name(
            "BT-TH-123456", default_device_type=const_module.DeviceType.DCC.value
        )
        == const_module.DeviceType.DCC.value
    )


def test_is_device_name_ready_by_device_type() -> None:
    """Readiness should enforce prefix by configured device type."""
    device_name_module = _load_device_name_module()
    const_module = importlib.import_module("custom_components.renogy.const")

    assert device_name_module.is_device_name_ready(
        "BT-TH-123456", const_module.DeviceType.CONTROLLER.value
    )
    assert device_name_module.is_device_name_ready(
        "RTMShunt300A1B2", const_module.DeviceType.SHUNT300.value
    )
    assert not device_name_module.is_device_name_ready(
        "RTMShunt300A1B2", const_module.DeviceType.CONTROLLER.value
    )
    assert not device_name_module.is_device_name_ready(
        "Unknown Renogy Device", const_module.DeviceType.SHUNT300.value
    )
