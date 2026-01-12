# renogy-ble Fork Changes for DCC Support

This document describes the changes needed in the `renogy-ble` library to support DCC (DC-DC) chargers and write operations.

## Overview

The renogy-ble library needs these modifications:
1. Add DCC device type register mappings
2. Add DCC commands for reading device data
3. Add `write_register()` function for parameter configuration

## File Changes

### 1. `register_map.py` - Add DCC Register Map

Add the following to `REGISTER_MAP`:

```python
"dcc": {
    # Device info section (register 12)
    "model": {
        "register": 12,
        "length": 14,
        "byte_order": "big",
        "offset": 3,
        "data_type": "string",
    },
    # Device address section (register 26)
    "device_id": {"register": 26, "length": 1, "byte_order": "big", "offset": 4},

    # Dynamic Data Section (register 256 / 0x0100)
    # Based on DCC Charger Controller Modbus Protocol V1.0
    "battery_soc": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 3,
    },
    "battery_voltage": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 5,
    },
    "total_charging_current": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.01,
        "offset": 7,
    },
    "alternator_voltage": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 11,
    },
    "alternator_current": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.01,
        "offset": 13,
    },
    "alternator_power": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 15,
    },
    "solar_voltage": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 17,
    },
    "solar_current": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.01,
        "offset": 19,
    },
    "solar_power": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 21,
    },
    "daily_min_battery_voltage": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 25,
    },
    "daily_max_battery_voltage": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 27,
    },
    "daily_max_charging_current": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.01,
        "offset": 29,
    },
    "daily_max_charging_power": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 33,
    },
    "daily_charging_ah": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 37,
    },
    "daily_power_generation": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "scale": 0.001,  # Returns kWh
        "offset": 41,
    },
    "total_operating_days": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 45,
    },
    "total_overdischarge_count": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 47,
    },
    "total_full_charge_count": {
        "register": 256,
        "length": 2,
        "byte_order": "big",
        "offset": 49,
    },
    "total_charging_ah": {
        "register": 256,
        "length": 4,
        "byte_order": "big",
        "offset": 51,
    },
    "total_power_generation": {
        "register": 256,
        "length": 4,
        "byte_order": "big",
        "scale": 0.001,  # Returns kWh
        "offset": 59,
    },

    # Charging status section (register 288 / 0x0120)
    "charging_status": {
        "register": 288,
        "length": 1,
        "byte_order": "big",
        "map": {
            0: "standby",
            2: "mppt",
            3: "equalizing",
            4: "boost",
            5: "floating",
            6: "current_limiting",
            8: "dc_mode",
        },
        "offset": 4,  # Low byte of 0x0120
    },

    # Fault information (register 289-290 / 0x0121-0x0122)
    "fault_high": {
        "register": 289,
        "length": 2,
        "byte_order": "big",
        "offset": 3,
    },
    "fault_low": {
        "register": 290,
        "length": 2,
        "byte_order": "big",
        "offset": 3,
    },

    # Actual charging power at output (register 292 / 0x0124)
    "output_power": {
        "register": 292,
        "length": 2,
        "byte_order": "big",
        "offset": 3,
    },

    # Charging mode (register 293 / 0x0125)
    "charging_mode": {
        "register": 293,
        "length": 2,
        "byte_order": "big",
        "map": {
            0: "standby",
            1: "alternator_to_house",
            2: "house_to_starter",
            3: "solar_to_house",
            4: "solar_alternator_to_house",
            5: "solar_to_starter",
        },
        "offset": 3,
    },

    # Ignition signal (register 294 / 0x0126)
    "ignition_status": {
        "register": 294,
        "length": 2,
        "byte_order": "big",
        "map": {0: "disconnected", 1: "connected"},
        "offset": 3,
    },

    # Parameter Settings Section (register 57347+ / 0xE003+)
    # These are read from a separate command
    "system_voltage": {
        "register": 57347,
        "length": 1,
        "byte_order": "big",
        "offset": 3,  # High byte
    },
    "battery_type": {
        "register": 57348,
        "length": 2,
        "byte_order": "big",
        "map": {0: "custom", 1: "open", 2: "sealed", 3: "gel", 4: "lithium"},
        "offset": 5,
    },
    "overvoltage_threshold": {
        "register": 57349,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 7,
    },
    "charging_limit_voltage": {
        "register": 57350,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 9,
    },
    "equalization_voltage": {
        "register": 57351,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 11,
    },
    "boost_voltage": {
        "register": 57352,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 13,
    },
    "float_voltage": {
        "register": 57353,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 15,
    },
    "boost_return_voltage": {
        "register": 57354,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 17,
    },
    "overdischarge_return_voltage": {
        "register": 57355,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 19,
    },
    "undervoltage_warning": {
        "register": 57356,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 21,
    },
    "overdischarge_voltage": {
        "register": 57357,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 23,
    },
    "discharge_limit_voltage": {
        "register": 57358,
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 25,
    },
    "overdischarge_delay": {
        "register": 57360,
        "length": 2,
        "byte_order": "big",
        "offset": 29,
    },
    "equalization_time": {
        "register": 57361,
        "length": 2,
        "byte_order": "big",
        "offset": 31,
    },
    "boost_time": {
        "register": 57362,
        "length": 2,
        "byte_order": "big",
        "offset": 33,
    },
    "equalization_interval": {
        "register": 57363,
        "length": 2,
        "byte_order": "big",
        "offset": 35,
    },
    "temperature_compensation": {
        "register": 57364,
        "length": 2,
        "byte_order": "big",
        "offset": 37,
    },

    # Additional parameters at different registers
    "reverse_charging_voltage": {
        "register": 57376,  # 0xE020
        "length": 2,
        "byte_order": "big",
        "scale": 0.1,
        "offset": 3,
    },
    "solar_cutoff_current": {
        "register": 57400,  # 0xE038
        "length": 2,
        "byte_order": "big",
        "offset": 3,
    },
}
```

### 2. `ble.py` - Add DCC Commands and Write Support

#### 2.1 Add DCC to COMMANDS dict:

```python
COMMANDS = {
    "controller": {
        "device_info": (3, 12, 8),
        "device_id": (3, 26, 1),
        "battery": (3, 57348, 1),
        "pv": (3, 256, 34),
    },
    "dcc": {
        "device_info": (3, 12, 8),
        "device_id": (3, 26, 1),
        "dynamic_data": (3, 256, 48),  # 0x0100-0x012F (48 words)
        "status": (3, 288, 8),  # 0x0120-0x0127 (8 words)
        "parameters": (3, 57347, 18),  # 0xE003-0xE014 (18 words)
    },
}
```

#### 2.2 Add write request builder function:

```python
def create_modbus_write_request(
    device_id: int, register: int, value: int
) -> bytearray:
    """Build a Modbus function 06 (write single register) frame.

    Args:
        device_id: Modbus device ID (1-247, or 0xFF for universal)
        register: Register address to write
        value: 16-bit value to write

    Returns:
        Complete Modbus frame with CRC
    """
    frame = bytearray(
        [
            device_id,
            0x06,  # Function code 06 = write single register
            (register >> 8) & 0xFF,
            register & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]
    )
    crc_low, crc_high = modbus_crc(frame)
    frame.extend([crc_low, crc_high])
    logger.debug("create_write_request: register=%s value=%s frame=%s",
                 hex(register), value, list(frame))
    return frame
```

#### 2.3 Add write_register method to RenogyBleClient:

```python
async def write_register(
    self, device: RenogyBLEDevice, register: int, value: int
) -> bool:
    """Write a single register value to the device.

    Args:
        device: The target device
        register: Register address to write (e.g., 0xE004 for battery type)
        value: 16-bit value to write

    Returns:
        True if write was successful, False otherwise
    """
    connection_kwargs = self._connection_kwargs()

    try:
        client = await establish_connection(
            BleakClientWithServiceCache,
            device.ble_device,
            device.name or device.address,
            max_attempts=self._max_attempts,
            **connection_kwargs,
        )
    except (BleakError, asyncio.TimeoutError) as connection_error:
        logger.error(
            "Failed to connect for write to device %s: %s",
            device.name,
            str(connection_error),
        )
        return False

    try:
        logger.debug("Connected to device %s for write", device.name)
        notification_event = asyncio.Event()
        notification_data = bytearray()

        def notification_handler(_sender, data):
            notification_data.extend(data)
            notification_event.set()

        await client.start_notify(self._read_char_uuid, notification_handler)

        # Build and send the write request
        modbus_request = create_modbus_write_request(
            self._device_id, register, value
        )
        logger.debug(
            "Sending write command to register %s: %s",
            hex(register),
            list(modbus_request),
        )
        await client.write_gatt_char(self._write_char_uuid, modbus_request)

        # Wait for response (function 06 echoes the request on success)
        expected_len = 8  # Same length as request
        try:
            await asyncio.wait_for(
                notification_event.wait(),
                self._max_notification_wait_time
            )
        except asyncio.TimeoutError:
            logger.error(
                "Timeout waiting for write response from device %s",
                device.name,
            )
            return False

        await client.stop_notify(self._read_char_uuid)

        # Verify response
        if len(notification_data) < expected_len:
            logger.error(
                "Write response too short: got %s bytes, expected %s",
                len(notification_data),
                expected_len,
            )
            return False

        # Check for error response (function code with high bit set)
        if notification_data[1] & 0x80:
            error_code = notification_data[2] if len(notification_data) > 2 else 0
            logger.error(
                "Modbus write error: function code %s, error code %s",
                notification_data[1],
                error_code,
            )
            return False

        # Verify the echoed register and value match
        resp_register = (notification_data[2] << 8) | notification_data[3]
        resp_value = (notification_data[4] << 8) | notification_data[5]

        if resp_register != register or resp_value != value:
            logger.error(
                "Write response mismatch: expected reg=%s val=%s, got reg=%s val=%s",
                hex(register), value, hex(resp_register), resp_value,
            )
            return False

        logger.info(
            "Successfully wrote value %s to register %s on device %s",
            value, hex(register), device.name,
        )
        return True

    except BleakError as exc:
        logger.error("BLE error during write to device %s: %s", device.name, str(exc))
        return False
    except Exception as exc:
        logger.error("Error writing to device %s: %s", device.name, str(exc))
        return False
    finally:
        if client.is_connected:
            try:
                await client.disconnect()
            except Exception as exc:
                logger.debug(
                    "Error disconnecting from device %s: %s",
                    device.name,
                    str(exc),
                )
```

## DCC Register Address Reference

Based on DCC Charger Controller Modbus Protocol V1.0:

### Readable Registers (Function 03)

| PDU Address | Description | Data Type |
|-------------|-------------|-----------|
| 0x001A | Device address | 1-247 |
| 0x0100 | Battery SOC | 0-100% |
| 0x0101 | Battery voltage | *0.1V |
| 0x0102 | Total charging current | *0.01A |
| 0x0104 | Alternator/Generator voltage | *0.1V |
| 0x0105 | Alternator charging current | *0.01A |
| 0x0106 | Alternator charging power | W |
| 0x0107 | Solar panel voltage | *0.1V |
| 0x0108 | Solar panel current | *0.01A |
| 0x0109 | Solar charging power | W |
| 0x010B | Daily min battery voltage | *0.1V |
| 0x010C | Daily max battery voltage | *0.1V |
| 0x010D | Daily max charging current | *0.01A |
| 0x010F | Daily max charging power | W |
| 0x0111 | Daily charging Ah | Ah |
| 0x0113 | Daily power generation | *0.001kWh |
| 0x0115 | Total operating days | days |
| 0x0116 | Total overdischarge count | count |
| 0x0117 | Total full charge count | count |
| 0x0118-0x0119 | Total charging Ah | Ah (32-bit) |
| 0x011C-0x011D | Total power generation | *0.001kWh (32-bit) |
| 0x0120 | Charging status | enum |
| 0x0121 | Fault high bits | bitfield |
| 0x0122 | Fault low bits | bitfield |
| 0x0124 | Output charging power | W |
| 0x0125 | Charging mode | enum |
| 0x0126 | Ignition signal status | 0/1 |

### Writable Registers (Function 06)

| PDU Address | Description | Range | Unit |
|-------------|-------------|-------|------|
| 0xE004 | Battery type | 0-4 | enum |
| 0xE005 | Overvoltage threshold | 70-170 | *0.1V |
| 0xE006 | Charging limit voltage | 70-170 | *0.1V |
| 0xE007 | Equalization voltage | 70-170 | *0.1V |
| 0xE008 | Boost voltage | 70-170 | *0.1V |
| 0xE009 | Float voltage | 70-170 | *0.1V |
| 0xE00A | Boost return voltage | 70-170 | *0.1V |
| 0xE00B | Overdischarge return voltage | 70-170 | *0.1V |
| 0xE00C | Undervoltage warning | 70-170 | *0.1V |
| 0xE00D | Overdischarge voltage | 70-170 | *0.1V |
| 0xE00E | Discharge limit voltage | 70-170 | *0.1V |
| 0xE010 | Overdischarge delay | 0-120 | seconds |
| 0xE011 | Equalization time | 0-300 | minutes |
| 0xE012 | Boost time | 10-300 | minutes |
| 0xE013 | Equalization interval | 0-255 | days |
| 0xE014 | Temp compensation | 0-5 | mV/C/2V |
| 0xE020 | Reverse charging voltage | 70-170 | *0.1V |
| 0xE038 | Solar cutoff current | 0-10 | A |

### Battery Type Values

| Value | Type |
|-------|------|
| 0 | Custom |
| 1 | Open (Flooded) |
| 2 | Sealed (AGM) |
| 3 | Gel |
| 4 | Lithium |

### Charging Status Values

| Value | Status | Description |
|-------|--------|-------------|
| 0 | Standby | Not charging |
| 2 | MPPT | Solar MPPT charging |
| 3 | Equalizing | Equalization charge |
| 4 | Boost | Bulk/absorption charge |
| 5 | Floating | Float/maintenance charge |
| 6 | Current Limiting | Current limited |
| 8 | DC Mode | Alternator/DC charging |

### Charging Mode Values

| Value | Mode | Description |
|-------|------|-------------|
| 0 | Standby | No active charging |
| 1 | Alternator to House | Starter battery charging house |
| 2 | House to Starter | House battery charging starter |
| 3 | Solar to House | Solar only to house battery |
| 4 | Solar+Alternator to House | Combined charging |
| 5 | Solar to Starter | Solar reverse charging starter |

## Testing Notes

For testing with RBC20D1U (non-MPPT model):
- Solar sensors will read 0 (no solar input)
- Primary input is alternator/starter battery
- Focus on alternator_* sensors
