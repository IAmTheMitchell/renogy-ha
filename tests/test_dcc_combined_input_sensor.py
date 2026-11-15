"""Regression tests for the DCC Combined Input Power sensor."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

from tests.test_sensor_setup import _load_sensor_module, _read_sensor_value


def test_dcc_exposes_combined_input_power_with_existing_sensors() -> None:
    """Expose one new DCC sensor without changing existing power keys."""
    module = _load_sensor_module()
    groups = module.SENSORS_BY_DEVICE_TYPE[module.DeviceType.DCC.value]
    status = {desc.key: desc for desc in groups["Status"]}
    solar = {desc.key: desc for desc in groups["Solar"]}
    alternator = {desc.key: desc for desc in groups["Alternator"]}

    assert module.KEY_COMBINED_INPUT_POWER in status
    assert module.KEY_SOLAR_POWER in solar
    assert module.KEY_ALTERNATOR_POWER in alternator

    combined = status[module.KEY_COMBINED_INPUT_POWER]
    assert combined.name == "Combined Input Power"
    assert combined.native_unit_of_measurement == module.UnitOfPower.WATT
    assert combined.device_class == module.SensorDeviceClass.POWER
    assert combined.state_class == module.SensorStateClass.MEASUREMENT
    assert combined.suggested_display_precision == 0


def test_combined_and_existing_power_sensors_keep_independent_values() -> None:
    """The HA layer reads three independent semantic fields from renogy-ble."""
    module = _load_sensor_module()
    dcc = module.SENSORS_BY_DEVICE_TYPE[module.DeviceType.DCC.value]
    descriptions = {desc.key: desc for group in dcc.values() for desc in group}
    readings = {
        "combined_input_power": 93,
        "alternator_power": 74,
        "solar_power": 19,
    }

    for key, expected in readings.items():
        assert _read_sensor_value(module, descriptions[key], readings) == expected


def test_other_device_types_do_not_gain_combined_dcc_input_sensor() -> None:
    """No extra DCC-specific entity on controllers, inverters or batteries."""
    module = _load_sensor_module()
    for device_type, groups in module.SENSORS_BY_DEVICE_TYPE.items():
        if device_type == module.DeviceType.DCC.value:
            continue
        assert all(
            desc.key != module.KEY_COMBINED_INPUT_POWER
            for group in groups.values()
            for desc in group
        )


def test_released_library_frames_reach_dcc_sensor_entities() -> None:
    """Exercise the installed library before HA test stubs replace its modules."""
    script = dedent(
        """
        from unittest.mock import MagicMock
        from renogy_ble import RenogyBLEDevice
        from tests.test_sensor_setup import _load_sensor_module

        module = _load_sensor_module()
        frames = [
            (
                "ff0340001b0083007e1f19007c00a500140000000000140000007c009e"
                "0e700000021e000000000000000b00000027000000090000061f00000000"
                "000059d500000000c0b6",
                {"combined_input_power": 20, "alternator_power": 20, "solar_power": 0},
            ),
            (
                "ff03400021008402552a19007c025b004a00b00070005d0013007c009e"
                "0e700000021e00000061000005ea000000270000000b0000068000000000"
                "00005fb4000000005817",
                {"combined_input_power": 93, "alternator_power": 74, "solar_power": 19},
            ),
        ]
        for model in ("RBC50D1S-G7", "RBC50D1S-G6", ""):
            ble_device = MagicMock(address="AA:BB:CC:DD:EE:FF")
            ble_device.name = "BT-TH-TEST"
            device = RenogyBLEDevice(ble_device, device_type="dcc")
            device.parsed_data["model"] = model
            coordinator = MagicMock(address=device.address, device=device)
            entities = {
                entity.entity_description.key: entity
                for entity in module.create_entities_helper(coordinator, device, "dcc")
            }
            for frame, expected in frames:
                assert device.update_parsed_data(
                    bytes.fromhex(frame), 0x0100, "dynamic_data"
                )
                coordinator.data = dict(device.parsed_data)
                for key, value in expected.items():
                    entity = entities[key]
                    entity._handle_coordinator_update()
                    if model != "RBC50D1S-G7":
                        value = None if key == "combined_input_power" else (
                            expected["combined_input_power"]
                            if key == "solar_power" else value
                        )
                    assert entity.native_value == value, (
                        model, key, entity.native_value
                    )
                    assert entity._attr_unique_id == f"{device.address}_{key}"
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
