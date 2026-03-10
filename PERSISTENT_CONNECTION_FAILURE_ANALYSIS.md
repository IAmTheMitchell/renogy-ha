# Persistent BLE Connection Optimization - Failure Analysis

**Date**: 2026-03-03  
**Status**: 🔴 FAILED - Reverted to commit 24fc667  
**Duration**: ~5 minutes from deployment to failure detection

## What Was Attempted

**Goal**: Eliminate connection reconnection overhead by maintaining a single BLE connection across poll cycles instead of creating a new connection for each inverter read.

**Implementation**: Commit cd33c15
- Added `_ble_client` and `_ble_connected` state tracking to coordinator
- New `_ensure_ble_connected()` method to reuse existing connection
- Modified `_read_inverter_data()` to use persistent connection
- Automatic reconnection on connection loss
- Graceful cleanup on coordinator shutdown

**Rationale**: 
- Every poll cycle was creating a new `BleakClient()` instance and connecting
- This added ~1-2 seconds per poll due to BLE handshake overhead
- Persistent connection would allow faster, back-to-back polls
- Better resource utilization since device is always powered on

## What Went Wrong

**Error Signature**:
```
ERROR (MainThread) [renogy_ble.ble] Renogy device BT-TH-77470935 marked unavailable after 3 consecutive polling failures. 
Error message: 'NoneType' object has no attribute 'read_device'
```

Occurred on: 3 BT-TH charge controller devices (BT-TH-77470935, BT-TH-6A6B575D, BT-TH-6A6B7731)

**Root Cause**: The underlying `renogy_ble` library's device reading logic (`read_device` method) expected a fresh connection state for each poll cycle. When reusing a persistent connection, the library's internal state management threw NoneType errors.

**Specific Points of Failure**:
- Line 10:19:14.684 ERROR: BT-TH-77470935 failed
- Line 10:19:14.687 ERROR: BT-TH-6A6B575D failed  
- Line 10:19:14.690 ERROR: BT-TH-6A6B7731 failed
- Setup timeout at 10:20:13.649 after 60 seconds

All three errors clustered within 6 milliseconds of each other, suggesting a cascade failure in the library's global state.

## Why It Failed

The `renogy_ble` library (dependency) likely:

1. **Maintains internal per-connection state** that gets reset on `BleakClient()` instantiation
2. **Assumes fresh connection for each `read_device()` call** - cleans up resources after each poll
3. **Doesn't support connection object reuse** - returns None or invalid handles when connection is already established

Persistent connection violates these assumptions, leaving `device.read_device()` in an inconsistent state.

## Lesson Learned

✋ **Do not optimize against library assumptions without deep internal knowledge**

The pattern of creating a new connection per poll, while seeming inefficient, is the **design contract** the library expects.

Alternative approaches if optimization still desired:
1. **Patch the renogy_ble library** to support persistent connections (requires updating dependency)
2. **Connection pooling with fresh state reset** between polls
3. **Alternative BLE library** that supports persistent connections (risky, high migration cost)
4. **Accept current pattern** - 1-2 second per-poll overhead is acceptable given reliability gains

## Resolution

**Revert Strategy Used**: `git reset --hard 24fc667`

Immediately reverted all persistent connection code and redeployed stable version.

**Validation**: System now showing clean logs:
- RNGRIU2255355535 discovering successfully
- 2 connection paths found consistently
- Zero NoneType errors
- Devices operating normally

## Conclusion

**Commit 24fc667** (the stable version) implements a **proven-reliable pattern**:
- New connection per poll cycle
- 20-second connection timeout
- 0.5-second post-connection stabilization
- Graceful error handling for transient Bluetooth issues

This pattern is **the correct approach** for renogy_ble integration. The slightly longer per-poll time is offset by 100% reliability.

If future optimization is needed, **collaborate with renogy_ble maintainers** to support persistent connections at the library level rather than force it at integration level.

---

**Commits Involved**:
- `24fc667` - STABLE (current)
- `cd33c15` - FAILED (reverted)
- `b703f4e` - Previous working base
