"""Modbus response helpers for Renogy BLE devices."""

from __future__ import annotations

from typing import Tuple


def normalize_modbus_response(
    raw_data: bytes, *, function_code: int, word_count: int, device_id: int
) -> Tuple[bytes, int, bool]:
    """Return a normalized Modbus response frame and the applied offset.

    This scans for a Modbus header that matches the expected function code and byte
    count so leading noise does not shift parsing offsets.
    """
    byte_count = word_count * 2
    expected_len = 3 + byte_count + 2

    if len(raw_data) == byte_count:
        frame = bytes([device_id, function_code, byte_count]) + raw_data + b"\x00\x00"
        return frame, 0, True

    if len(raw_data) == byte_count + 2:
        frame = bytes([device_id, function_code, byte_count]) + raw_data
        return frame, 0, True

    if len(raw_data) < expected_len:
        return raw_data, 0, False

    if raw_data[1] == function_code and raw_data[2] == byte_count:
        return raw_data[:expected_len], 0, False

    max_start = len(raw_data) - expected_len
    for start in range(1, max_start + 1):
        if raw_data[start + 1] != function_code:
            continue
        if raw_data[start + 2] != byte_count:
            continue
        return raw_data[start : start + expected_len], start, False

    for start in range(1, len(raw_data) - 4):
        if raw_data[start + 1] != function_code:
            continue
        candidate_count = raw_data[start + 2]
        candidate_len = 3 + candidate_count + 2
        if candidate_len <= 0:
            continue
        if start + candidate_len > len(raw_data):
            continue
        return raw_data[start : start + candidate_len], start, False

    return raw_data[:expected_len], 0, False
