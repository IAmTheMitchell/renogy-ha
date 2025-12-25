"""Tests for Modbus response normalization."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_modbus_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "renogy"
        / "modbus.py"
    )
    spec = spec_from_file_location("renogy_modbus", module_path)
    module = module_from_spec(spec)
    if spec.loader is None:
        raise ImportError("Unable to load renogy_modbus module.")
    spec.loader.exec_module(module)
    return module


normalize_modbus_response = _load_modbus_module().normalize_modbus_response


def test_normalize_modbus_response_no_prefix():
    """Keep a correctly framed response unchanged."""
    raw_data = bytes([0xFF, 0x03, 0x04, 0x10, 0x11, 0x12, 0x13, 0xAA, 0xBB])

    frame, offset, padded = normalize_modbus_response(
        raw_data, function_code=0x03, word_count=2, device_id=0xFF
    )

    assert frame == raw_data
    assert offset == 0
    assert padded is False


def test_normalize_modbus_response_with_prefix():
    """Strip leading noise before the Modbus header."""
    raw_data = bytes(
        [
            0x00,
            0x00,
            0xFF,
            0x03,
            0x04,
            0x10,
            0x11,
            0x12,
            0x13,
            0xAA,
            0xBB,
        ]
    )

    frame, offset, padded = normalize_modbus_response(
        raw_data, function_code=0x03, word_count=2, device_id=0xFF
    )

    assert frame == bytes([0xFF, 0x03, 0x04, 0x10, 0x11, 0x12, 0x13, 0xAA, 0xBB])
    assert offset == 2
    assert padded is False


def test_normalize_modbus_response_with_suffix():
    """Trim trailing bytes after a valid frame."""
    raw_data = bytes(
        [
            0xFF,
            0x03,
            0x04,
            0x10,
            0x11,
            0x12,
            0x13,
            0xAA,
            0xBB,
            0x99,
        ]
    )

    frame, offset, padded = normalize_modbus_response(
        raw_data, function_code=0x03, word_count=2, device_id=0xFF
    )

    assert frame == bytes([0xFF, 0x03, 0x04, 0x10, 0x11, 0x12, 0x13, 0xAA, 0xBB])
    assert offset == 0
    assert padded is False


def test_normalize_modbus_response_payload_only():
    """Add a header when only the payload is provided."""
    raw_data = bytes([0x10, 0x11, 0x12, 0x13])

    frame, offset, padded = normalize_modbus_response(
        raw_data, function_code=0x03, word_count=2, device_id=0xFF
    )

    assert frame == bytes([0xFF, 0x03, 0x04, 0x10, 0x11, 0x12, 0x13, 0x00, 0x00])
    assert offset == 0
    assert padded is True


def test_normalize_modbus_response_payload_with_crc():
    """Add a header when payload includes CRC bytes."""
    raw_data = bytes([0x10, 0x11, 0x12, 0x13, 0xAA, 0xBB])

    frame, offset, padded = normalize_modbus_response(
        raw_data, function_code=0x03, word_count=2, device_id=0xFF
    )

    assert frame == bytes([0xFF, 0x03, 0x04, 0x10, 0x11, 0x12, 0x13, 0xAA, 0xBB])
    assert offset == 0
    assert padded is True
