"""Renogy Smart SHUNT BLE packet parser."""

import logging
from typing import Optional

LOGGER = logging.getLogger(__name__)

# BLE Characteristic UUIDs for SHUNT
SHUNT_SERVICE_UUID = "0000c011-0000-1000-8000-00805f9b34fb"
SHUNT_TX_UUID = "0000c111-0000-1000-8000-00805f9b34fb"  # Write commands
SHUNT_RX_UUID = "0000c411-0000-1000-8000-00805f9b34fb"  # Telemetry notifications


def bytes_to_int(
    data: bytes, offset: int, length: int, signed: bool = False, scale: float = 1.0
) -> float:
    """Convert bytes to integer with optional scaling.
    
    Args:
        data: Byte array to read from
        offset: Starting byte offset
        length: Number of bytes to read
        signed: If True, interpret as signed integer
        scale: Scaling factor to apply to result
    
    Returns:
        Scaled value as float
    """
    if len(data) < (offset + length):
        LOGGER.warning(
            "Insufficient data for read at offset %d length %d (data len %d)",
            offset,
            length,
            len(data),
        )
        return 0.0
    
    value = int.from_bytes(
        data[offset : offset + length],
        byteorder="big",
        signed=signed,
    )
    return round(value * scale, 2)


def parse_shunt_packet(data: bytes) -> Optional[dict]:
    """Parse Renogy Smart SHUNT 110-byte telemetry packet.
    
    Packet structure (110 bytes):
    - Bytes 0-1:   Header (0x42 0x57 = "BW")
    - Bytes 2-3:   Sequence number (increments each packet)
    - Bytes 4-20:  Reserved/Unknown
    - Bytes 21-23: Discharge Current (scale 0.001 A, SIGNED)
    - Bytes 24:    Unknown
    - Bytes 25-27: Charge Battery Voltage (scale 0.001 V)
    - Bytes 28-29: Unknown
    - Bytes 30-31: Starter Battery Voltage (scale 0.001 V)
    - Bytes 32-33: Unknown
    - Bytes 34-35: State of Charge (scale 0.1 %)
    - Bytes 36+:   Additional fields (unused)
    
    Args:
        data: Raw BLE notification packet (110 bytes)
    
    Returns:
        Dictionary with parsed telemetry, or None if invalid
    """
    # Validate packet structure
    if not data:
        LOGGER.warning("Empty SHUNT packet")
        return None
    
    if len(data) < 36:
        LOGGER.warning("SHUNT packet too short: %d bytes (expected 110)", len(data))
        return None
    
    # Verify header
    if data[0:2] != b"BW":
        LOGGER.warning(
            "Invalid SHUNT packet header: 0x%s (expected 0x4257)",
            data[0:2].hex(),
        )
        return None
    
    try:
        # Parse all fields
        sequence = int.from_bytes(data[2:4], byteorder="big", signed=False)
        battery_voltage = bytes_to_int(data, 25, 3, scale=0.001)
        battery_current = bytes_to_int(data, 21, 3, signed=True, scale=0.001)
        starter_voltage = bytes_to_int(data, 30, 2, scale=0.001)
        state_of_charge = bytes_to_int(data, 34, 2, scale=0.1)
        
        # Calculate power
        power = round(battery_voltage * battery_current, 2)
        
        result = {
            "sequence": sequence,
            "battery_voltage": battery_voltage,
            "battery_current": battery_current,
            "starter_voltage": starter_voltage,
            "state_of_charge": state_of_charge,
            "power": power,
            "rssi": None,  # Will be populated by caller
        }
        
        LOGGER.debug(
            "Parsed SHUNT packet (seq=%d): V=%.3f A=%.3f SOC=%.1f%%",
            int(sequence),
            battery_voltage,
            battery_current,
            state_of_charge,
        )
        
        return result
    
    except Exception as err:
        LOGGER.error("Error parsing SHUNT packet: %s", err)
        return None


def validate_shunt_packet(data: bytes) -> bool:
    """Quick validation check for SHUNT packet.
    
    Args:
        data: Raw packet data
    
    Returns:
        True if packet appears to be valid SHUNT format
    """
    if len(data) < 36:
        return False
    
    if data[0:2] != b"BW":
        return False
    
    return True
