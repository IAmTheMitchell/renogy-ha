"""Modbus response helpers for Renogy BLE devices."""

from __future__ import annotations

from typing import Tuple


def normalize_modbus_response(
    raw_data: bytes, *, function_code: int, word_count: int
) -> Tuple[bytes, int]:
    """Return a normalized Modbus response frame and the applied offset.

    This scans for a Modbus header that matches the expected function code and byte
    count so leading noise does not shift parsing offsets.
    """
    byte_count = word_count * 2
    expected_len = 3 + byte_count + 2

    if len(raw_data) < expected_len:
        return raw_data, 0

    if raw_data[1] == function_code and raw_data[2] == byte_count:
        return raw_data[:expected_len], 0

    max_start = len(raw_data) - expected_len
    for start in range(1, max_start + 1):
        if raw_data[start + 1] != function_code:
            continue
        if raw_data[start + 2] != byte_count:
            continue
        return raw_data[start : start + expected_len], start

    return raw_data[:expected_len], 0
