"""Regression tests for the DCC Combined Input Power sensor."""

from __future__ import annotations

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
