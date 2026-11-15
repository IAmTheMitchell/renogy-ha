"""Exercise HA classification with real library metadata and device objects."""

import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def test_real_library_identification_contract():
    """Global transport mocks must not hide cross-repository disagreement."""
    script = dedent(
        """
        from unittest.mock import MagicMock
        from renogy_ble import RenogyBLEDevice, identify_advertisement
        from tests.test_config_flow import _load_config_flow_module
        from tests.test_ble import _load_ble_module

        flow = _load_config_flow_module()
        cases = [
            ("BT-TH-123", "controller", None),
            ("BT-TH-BATT01", "battery", "legacy"),
            ("RNGRBP123", "battery", "pro"),
            ("RNGC123", "battery", "pro"),
            ("RNGPRO123", "battery", "rngpro"),
            ("RNGRIU123", "inverter", None),
            ("BTRIC123", "inverter", None),
            ("RTMShunt300123", "shunt300", None),
        ]
        for name, expected_type, expected_variant in cases:
            info = flow.BluetoothServiceInfoBleak("AA:BB:CC:DD:EE:FF", name)
            assert flow.RenogyConfigFlow()._is_renogy_device(info)
            assert flow._detect_device_type_for_discovery(info) == expected_type
            device = RenogyBLEDevice(
                info.device, device_type=expected_type, advertisement_name=name,
            )
            assert device.battery_variant == expected_variant
            assert identify_advertisement(name).battery_variant == expected_variant

        module = _load_ble_module()
        module.RenogyBLEDevice = RenogyBLEDevice
        address = "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
        coordinator = module.RenogyActiveBluetoothCoordinator(
            hass=MagicMock(), logger=MagicMock(), address=address,
            device_type="battery", device_name="RNGPRO-stored",
        )
        first = module.BluetoothServiceInfoBleak(address=address, name=address)
        first.advertisement.manufacturer_data = {0xE14C: b""}
        first.advertisement.local_name = None
        device = coordinator._update_device_from_service_info(first)
        assert device.advertised_name == "RNGPRO-stored"
        assert device.battery_variant == "rngpro"
        first.advertisement.manufacturer_data = {}
        coordinator._update_device_from_service_info(first)
        assert device.manufacturer_data == {0xE14C: b""}
        assert device.advertised_name == "RNGPRO-stored"

        later = module.BluetoothServiceInfoBleak(address=address, name="RNGRBP-current")
        later.advertisement.local_name = "RNGRBP-current"
        coordinator._update_device_from_service_info(later)
        device.name = "Hardware display name"
        device.parsed_data["device_name"] = device.name
        first.device.name = "RNGPRO-old-OS-name"
        coordinator._update_device_from_service_info(first)
        assert device.advertised_name == "RNGRBP-current"
        assert device.name == "Hardware display name"
        from custom_components.renogy.device_name import is_device_name_ready
        assert is_device_name_ready(device.advertised_name, "battery", address)

        coordinator = module.RenogyActiveBluetoothCoordinator(
            hass=MagicMock(), logger=MagicMock(), address=address,
        )
        first.device.name = address
        first.advertisement.manufacturer_data = {0xE14C: b""}
        device = coordinator._update_device_from_service_info(first)
        assert device.device_type == "battery"
        assert device.battery_variant == "pro"
        first.advertisement.manufacturer_data = {}
        coordinator._update_device_from_service_info(first)
        assert device.manufacturer_data == {0xE14C: b""}
        assert device.battery_variant == "pro"

        for selected_type in ("controller", "dcc", "battery"):
            coordinator = module.RenogyActiveBluetoothCoordinator(
                hass=MagicMock(), logger=MagicMock(), address=address,
                device_type=selected_type, device_name="BT-TH-configured",
            )
            info = module.BluetoothServiceInfoBleak(address=address, name=address)
            info.advertisement.local_name = None
            device = coordinator._update_device_from_service_info(info)
            assert device.device_type == selected_type
            assert coordinator.device_type == selected_type
            assert device.battery_variant is None

        coordinator = module.RenogyActiveBluetoothCoordinator(
            hass=MagicMock(), logger=MagicMock(), address=address,
            device_type="inverter", model_hint="RIV4835CSH1S",
        )
        info = module.BluetoothServiceInfoBleak(address=address, name="BTRIC123")
        device = coordinator._update_device_from_service_info(info)
        coordinator._update_device_from_service_info(info)
        assert device.device_type == "inverter"
        assert device.model_hint == "RIV4835CSH1S"
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
