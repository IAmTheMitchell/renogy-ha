"""Isolated HA adapter scenario executed by integration tests."""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import renogy_ble as library
from renogy_ble import ble as library_transport

from tests.test_ble import _load_ble_module
from tests.test_number import _load_number_module, _load_select_module
from tests.test_switch import _load_switch_module

assert callable(getattr(library.RenogyBleClient, "write_setting", None))
ha_ble = _load_ble_module()
sys.modules["renogy_ble"] = library
sys.modules["renogy_ble.ble"] = library_transport


class Gatt:
    is_connected = True

    def __init__(self):
        self.requests = []
        self.fail = False

    async def start_notify(self, target, handler):
        self.handler = handler

    async def write_gatt_char(self, target, payload):
        request = bytes(payload)
        self.requests.append(request)
        if self.fail:
            response = bytes([request[0], 0x86, 2])
            response += bytes(library.modbus_crc(response))
        else:
            response = request
        self.handler(None, response)

    async def read_gatt_char(self, target):
        return b"\x00"

    async def stop_notify(self, target):
        pass

    async def disconnect(self):
        pass


gatt = Gatt()
library_transport.establish_connection = AsyncMock(return_value=gatt)
library_transport.INVERTER_INIT_DELAY = 0.0
kind = sys.argv[1]
name = "BTRIC-test" if kind == "rego" else "BT-TH-test"
device_type = "inverter" if kind in ("rego", "riv") else kind
model = "RIV4835CSH1S" if kind == "riv" else None
ble_device = MagicMock(address="AA:BB:CC:DD:EE:FF")
ble_device.name = name
device = library.RenogyBLEDevice(ble_device, device_type=device_type, model_hint=model)
coordinator = ha_ble.RenogyActiveBluetoothCoordinator(
    hass=MagicMock(),
    logger=MagicMock(),
    address=device.address,
    device_type=device_type,
    model_hint=model,
)
coordinator.device = device
coordinator._ble_client = library.RenogyBleClient()
coordinator.async_request_refresh = AsyncMock()
coordinator.data = {}


async def run():
    if kind in ("dcc", "controller"):
        select = _load_select_module()
        entity = select.RenogyBatteryTypeSelect(
            coordinator, device, select.BATTERY_TYPE_DESCRIPTION, kind
        )
        entity.async_write_ha_state = MagicMock()
        await entity.async_select_option("Custom")
        code = 0 if kind == "dcc" else 5
        assert gatt.requests[-1][:6] == bytes([255, 6, 224, 4, 0, code])
        assert entity.current_option == "Custom"
        gatt.fail = True
        await entity.async_select_option("Gel")
        assert entity.current_option == "Custom"
        # Decode a real library read response and let HA publish its semantic type.
        response = bytes([255, 3, 2, 0, 3])
        response += bytes(library.modbus_crc(response))
        register = 0xE004 if kind == "controller" else 0xE003
        if kind == "dcc":
            response = bytes([255, 3, 4, 0, 12, 0, 3])
            response += bytes(library.modbus_crc(response))
        device.parsed_data = library.RenogyParser.parse(response, kind, register)
        entity._handle_coordinator_update()
        assert entity.current_option == "Gel"
    else:
        number = _load_number_module()
        description = (
            number.RIV4835CSH1S_NUMBERS[0]
            if kind == "riv"
            else next(
                d
                for d in number.INVERTER_ALL_NUMBERS
                if d.key == "inverter_low_voltage_warn"
            )
        )
        entity = number.RenogyNumberEntity(
            coordinator, device, description, device_type
        )
        entity.async_write_ha_state = MagicMock()
        value = 10.0 if kind == "riv" else 14.3
        register = 0xE205 if kind == "riv" else 0x114E
        wire = 100 if kind == "riv" else 143
        await entity.async_set_native_value(value)
        assert gatt.requests[-1][:6] == bytes([32, 6]) + register.to_bytes(
            2, "big"
        ) + wire.to_bytes(2, "big")
        assert entity.native_value == value
        gatt.fail = True
        await entity.async_set_native_value(5.0 if kind == "riv" else 12.3)
        assert entity.native_value == value
        response = bytes([32, 3, 2, 0, 50 if kind == "riv" else 123])
        response += bytes(library.modbus_crc(response))
        device.parsed_data = library.RenogyBleClient._parse_inverter_setpoint(
            response, description.key
        )
        entity._handle_coordinator_update()
        assert entity.native_value == (5.0 if kind == "riv" else 12.3)
    if kind == "controller":
        switch_module = _load_switch_module()
        switch = switch_module.RenogyLoadSwitch(coordinator, device, "controller")
        switch.async_write_ha_state = MagicMock()
        coordinator._service_info_for_operation = MagicMock(return_value=MagicMock())
        coordinator._update_device_from_service_info = MagicMock(return_value=device)
        coordinator.async_update_listeners = MagicMock()
        gatt.fail = False
        await switch.async_turn_on()
        assert gatt.requests[-1][:6] == bytes([255, 6, 1, 10, 0, 1])
        assert switch.is_on
        gatt.fail = True
        await switch.async_turn_off()
        assert switch.is_on
        assert coordinator.data["load_status"] == "on"
        device.parsed_data["load_status"] = "off"
        switch._handle_coordinator_update()
        assert not switch.is_on
    assert entity._attr_unique_id == f"{device.address}_{entity.entity_description.key}"
    assert coordinator.async_request_refresh.await_count == 1


asyncio.run(run())
