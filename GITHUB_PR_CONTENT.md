# PR Title
fix: stabilize shunt BLE connection and RSSI reporting

## Summary
- Use `bleak_retry_connector.establish_connection()` for SHUNT BLE sessions to eliminate direct `.connect()` warnings.
- Parse and expose SHUNT RSSI from BLE advertisement data for signal strength sensor reliability.
- Add RSSI fallback logic in sensor layer to prevent `unknown` values.

## Validation
- 1-hour live monitoring completed
- 0 errors/exceptions
- 0 bleak-retry-connector warnings
- SHUNT RSSI observed (avg ~-41.82 dBm)

## Notes
No breaking changes expected. This aligns with Home Assistant BLE connection best practices.
