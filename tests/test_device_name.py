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
    assert device_name_module.is_supported_renogy_ble_name("BT-TH-BATT01")
    assert device_name_module.is_supported_renogy_ble_name("RNGRIU123456")
    assert device_name_module.is_supported_renogy_ble_name("RNGRBP123456")
    assert device_name_module.is_supported_renogy_ble_name("RNGC123456")
    assert device_name_module.is_supported_renogy_ble_name("RNGPRO125BAT-EF036881")
    assert device_name_module.is_supported_renogy_ble_name(
        None, manufacturer_data={0xE14C: b"\x01"}
    )
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
        device_name_module.detect_device_type_from_ble_name("RNGRIU123456")
        == const_module.DeviceType.INVERTER.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name("RNGRBP123456")
        == const_module.DeviceType.BATTERY.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name("RNGC123456")
        == const_module.DeviceType.BATTERY.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name("RNGPRO125BAT-EF036881")
        == const_module.DeviceType.BATTERY.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name("BT-TH-BATTERY01")
        == const_module.DeviceType.BATTERY.value
    )
    assert (
        device_name_module.detect_device_type_from_ble_name(
            None, manufacturer_data={0xE14C: b"\x01"}
        )
        == const_module.DeviceType.BATTERY.value
    )
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
    assert device_name_module.is_device_name_ready(
        "RNGRIU123456", const_module.DeviceType.INVERTER.value
    )
    assert device_name_module.is_device_name_ready(
        "RNGRBP123456", const_module.DeviceType.BATTERY.value
    )
    assert device_name_module.is_device_name_ready(
        "RNGPRO125BAT-EF036881", const_module.DeviceType.BATTERY.value
    )
    assert device_name_module.is_device_name_ready(
        "BT-TH-BATTERY01", const_module.DeviceType.BATTERY.value
    )
    assert not device_name_module.is_device_name_ready(
        "RTMShunt300A1B2", const_module.DeviceType.CONTROLLER.value
    )
    assert not device_name_module.is_device_name_ready(
        "Unknown Renogy Device", const_module.DeviceType.SHUNT300.value
    )


def test_detect_device_type_from_model_identifies_dcc_chargers() -> None:
    """DC-DC charger model strings should map to the DCC device type."""
    device_name_module = _load_device_name_module()
    const_module = importlib.import_module("custom_components.renogy.const")

    for model in ("DCC50S", "DCC30S", "RBC20D1U", "RBC50D1S-G6", "rbc30d1s"):
        assert (
            device_name_module.detect_device_type_from_model(model)
            == const_module.DeviceType.DCC.value
        ), model


def test_detect_device_type_from_model_ignores_other_models() -> None:
    """Non-DCC or unusable model strings should not suggest a device type."""
    device_name_module = _load_device_name_module()

    assert device_name_module.detect_device_type_from_model("RNG-CTRL-RVR40") is None
    assert device_name_module.detect_device_type_from_model("RBT100LFP12S") is None
    assert device_name_module.detect_device_type_from_model("RBC1218S0") is None
    assert device_name_module.detect_device_type_from_model("") is None
    assert device_name_module.detect_device_type_from_model("   ") is None
    assert device_name_module.detect_device_type_from_model(None) is None


def test_btric_inverter_name_is_supported():
    device_name_module = _load_device_name_module()
    assert device_name_module.is_supported_renogy_ble_name("BTRIC130000029")


def test_btric_inverter_type_detected():
    device_name_module = _load_device_name_module()
    const_module = importlib.import_module("custom_components.renogy.const")
    assert (
        device_name_module.detect_device_type_from_ble_name("BTRIC130000029")
        == const_module.DeviceType.INVERTER.value
    )


def test_btric_inverter_name_ready():
    device_name_module = _load_device_name_module()
    const_module = importlib.import_module("custom_components.renogy.const")
    assert device_name_module.is_device_name_ready(
        "BTRIC130000029", const_module.DeviceType.INVERTER.value
    )


def test_bare_address_is_not_a_real_name() -> None:
    """A BD address reaching us as a "name" must not be trusted.

    Observed on a Pi with only its built-in adapter: Home Assistant's default
    ``auto`` scanning mode resolves to passive, no advertisement then carries a
    local name, and HA names each one after its address. That string was
    accepted as real, overwrote the cached name, and battery variant detection
    -- which matches the RNGPRO/RBT prefix -- failed with
    "Unable to determine Renogy battery variant for 14:9C:EF:03:68:81".
    """
    device_name_module = _load_device_name_module()

    # The habluetooth fallback: name is the address, verbatim.
    assert not device_name_module.has_real_device_name(
        "14:9C:EF:03:68:81", "14:9C:EF:03:68:81"
    )
    # Case must not matter -- BlueZ upper-cases, some backends do not.
    assert not device_name_module.has_real_device_name(
        "c4:d3:6a:8c:b5:38", "C4:D3:6A:8C:B5:38"
    )
    # The BlueZ Alias fallback: address with ":" replaced by "-". bleak
    # normalises this away before it reaches us; checked anyway.
    assert not device_name_module.has_real_device_name(
        "C4-D3-6A-8C-B5-38", "C4:D3:6A:8C:B5:38"
    )
    assert not device_name_module.has_real_device_name(
        "  14:9C:EF:03:68:81  ", "14:9C:EF:03:68:81"
    )


def test_a_macos_uuid_address_is_not_a_real_name() -> None:
    """BLEDevice.address is a UUID on macOS, so no MAC-shaped pattern can spot
    the placeholder there. Comparing against the address does."""
    device_name_module = _load_device_name_module()

    uuid = "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
    assert not device_name_module.has_real_device_name(uuid, uuid)


def test_real_names_still_pass() -> None:
    """The tightening must not reject anything that is actually a name."""
    device_name_module = _load_device_name_module()

    address = "14:9C:EF:03:68:81"
    assert device_name_module.has_real_device_name("RNGPRO125BAT-EF036881", address)
    assert device_name_module.has_real_device_name("BT-TH-6A8CB538", address)
    # A name that merely looks address-shaped is still a name: only the
    # device's own address is a placeholder.
    assert device_name_module.has_real_device_name("C4:D3:6A:8C:B5:38", address)
    assert device_name_module.has_real_device_name("14:9C:EF")
