"""RIV4835CSH1S Program 01 output-priority transactions."""

from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from renogy_ble.ble import (
    INVERTER_COMMAND_TIMEOUT,
    INVERTER_DEVICE_ID,
    INVERTER_INIT_CHAR_UUID,
    INVERTER_INIT_DELAY,
    create_modbus_write_request,
)

from .const import LOGGER, RIV4835CSH1SRegister

OUTPUT_PRIORITY_BY_RAW = {0: "SOL", 1: "UTI", 2: "SBU"}
OUTPUT_PRIORITY_TO_RAW = {value: key for key, value in OUTPUT_PRIORITY_BY_RAW.items()}


async def _prepare_locked_session(coordinator: Any) -> tuple[Any, Any, Any]:
    """Resolve the current Renogy device/client and prepare its BLE session."""
    client = getattr(coordinator, "_ble_client", None)
    if client is None:
        raise HomeAssistantError("Renogy BLE client is unavailable.")

    service_info_fn = getattr(coordinator, "_service_info_for_operation", None)
    service_info = service_info_fn() if callable(service_info_fn) else None

    if service_info is not None:
        update_device_fn = getattr(coordinator, "_update_device_from_service_info", None)
        if not callable(update_device_fn):
            raise HomeAssistantError(
                "Renogy coordinator cannot refresh BLE device context."
            )
        device = update_device_fn(service_info)
    else:
        device = getattr(coordinator, "device", None)

    if device is None:
        raise HomeAssistantError(
            "Renogy inverter has not been discovered yet. Wait for a normal poll and retry."
        )

    prepare_session = getattr(client, "_prepare_session", None)
    ensure_session_ready = getattr(client, "_ensure_session_ready", None)
    if not callable(prepare_session) or not callable(ensure_session_ready):
        raise HomeAssistantError(
            "Installed renogy-ble does not expose the session methods required for "
            "RIV4835 output-priority control."
        )

    session = await prepare_session(device)
    return client, device, session


async def _init_inverter_session(client: Any, device: Any, session: Any) -> None:
    """Initialize the inverter BLE session before a Modbus transaction."""
    ensure_session_ready = getattr(client, "_ensure_session_ready", None)
    if not callable(ensure_session_ready):
        raise HomeAssistantError("Renogy BLE session preparation is unavailable.")

    await ensure_session_ready(device, session)
    if session.client is None:
        raise HomeAssistantError("Renogy BLE session is not connected.")

    await asyncio.sleep(INVERTER_INIT_DELAY)
    try:
        await session.client.read_gatt_char(INVERTER_INIT_CHAR_UUID)
    except Exception as exc:  # noqa: BLE001
        LOGGER.debug("RIV4835 output-priority inverter init read failed: %s", exc)


async def _read_from_session(client: Any, device: Any, session: Any) -> int:
    """Read exactly one Program 01 register value from the active session."""
    read_modbus_register = getattr(client, "_read_modbus_register", None)
    if not callable(read_modbus_register):
        raise HomeAssistantError(
            "Installed renogy-ble does not expose the validated Modbus read method."
        )

    response = await read_modbus_register(
        session,
        device_id=INVERTER_DEVICE_ID,
        function_code=0x03,
        register=RIV4835CSH1SRegister.OUTPUT_PRIORITY,
        word_count=1,
        cmd_name="RIV4835 Program 01 output-priority read",
        device_name=device.name,
        timeout=INVERTER_COMMAND_TIMEOUT,
        retries=1,
    )

    if response is None:
        raise HomeAssistantError(
            "No valid Modbus response received for Program 01 register 0x1159."
        )
    if len(response) < 7 or response[1] != 0x03 or response[2] != 0x02:
        raise HomeAssistantError(
            f"Unexpected Modbus response for Program 01: {response.hex()}"
        )

    raw = int.from_bytes(response[3:5], "big", signed=False)
    if raw not in OUTPUT_PRIORITY_BY_RAW:
        raise HomeAssistantError(
            f"Unexpected Program 01 raw value {raw}; refusing to infer a mode."
        )
    return raw


async def _write_to_session(
    client: Any,
    device: Any,
    session: Any,
    target: int,
) -> None:
    """Issue exactly one F06 write to Program 01 on the active locked session."""
    if target not in {1, 2}:
        raise HomeAssistantError(
            "Program 01 write is limited to hardware-validated values 1=UTI and 2=SBU."
        )

    reset_notifications = getattr(client, "_reset_notifications", None)
    wait_for_write_response = getattr(client, "_wait_for_write_response", None)
    if not callable(reset_notifications) or not callable(wait_for_write_response):
        raise HomeAssistantError(
            "Installed renogy-ble does not expose the validated write-response methods."
        )

    if session.client is None:
        raise HomeAssistantError("Renogy BLE session is not connected.")

    reset_notifications(session)
    write_target = getattr(session, "write_target", None) or getattr(
        client, "_write_char_uuid", None
    )
    if write_target is None:
        raise HomeAssistantError("Renogy BLE write characteristic is unavailable.")

    request = create_modbus_write_request(
        INVERTER_DEVICE_ID,
        RIV4835CSH1SRegister.OUTPUT_PRIORITY,
        target,
        function_code=0x06,
    )

    LOGGER.debug(
        "RIV4835 Program 01 write register=0x1159 target=%d decoded=%s request=%s",
        target,
        OUTPUT_PRIORITY_BY_RAW[target],
        request.hex(),
    )

    await session.client.write_gatt_char(write_target, request)
    try:
        await wait_for_write_response(
            session,
            RIV4835CSH1SRegister.OUTPUT_PRIORITY,
            request,
            0x06,
        )
    except asyncio.TimeoutError as err:
        raise HomeAssistantError(
            "Timed out waiting for the Program 01 F06 write acknowledgement."
        ) from err


async def _close_session_if_needed(client: Any, device: Any, session: Any) -> None:
    """Close an intermittent or desynchronized session after the transaction."""
    close_session = getattr(client, "_close_session", None)
    if not callable(close_session):
        return

    desynchronized = bool(getattr(session, "desynchronized", False))
    transport_mode = getattr(
        client,
        "transport_mode",
        getattr(client, "_transport_mode", "per_operation"),
    )
    if desynchronized:
        await close_session(device.address, device.name, session, remove=True)
    elif transport_mode != "persistent_session":
        await close_session(device.address, device.name, session, remove=False)


async def _run_transaction(coordinator: Any, target: int | None) -> int:
    """Run one locked read or hardware-validated write/readback transaction."""
    if target is not None and target not in {1, 2}:
        raise HomeAssistantError(
            "Program 01 write is limited to hardware-validated values 1=UTI and 2=SBU."
        )

    if getattr(coordinator, "_connection_in_progress", False):
        raise HomeAssistantError(
            "Renogy coordinator is busy. Wait for the current poll to finish and retry."
        )

    connection_lock = getattr(coordinator, "_connection_lock", None)
    if connection_lock is None:
        raise HomeAssistantError("Renogy coordinator connection lock is unavailable.")

    async with connection_lock:
        coordinator._connection_in_progress = True
        client = device = session = None
        try:
            client, device, session = await _prepare_locked_session(coordinator)
            async with session.lock:
                await _init_inverter_session(client, device, session)
                current = await _read_from_session(client, device, session)

                if target is None or current == target:
                    return current

                # The only hardware-validated F06 transitions are UTI->SBU and
                # SBU->UTI. If the LCD was manually put in SOL, represent that
                # truthfully but require a manual return to UTI before writes resume.
                if (current, target) not in {(1, 2), (2, 1)}:
                    raise HomeAssistantError(
                        "Refusing unvalidated Program 01 transition: "
                        f"{OUTPUT_PRIORITY_BY_RAW[current]} -> "
                        f"{OUTPUT_PRIORITY_BY_RAW[target]}. Return Program 01 to UTI "
                        "manually if the inverter is currently in SOL."
                    )

                await _write_to_session(client, device, session, target)
                await asyncio.sleep(1.0)
                verified = await _read_from_session(client, device, session)
                if verified != target:
                    raise HomeAssistantError(
                        "Program 01 write was acknowledged but live readback did not match: "
                        f"target={target}/{OUTPUT_PRIORITY_BY_RAW[target]}, "
                        f"readback={verified}/{OUTPUT_PRIORITY_BY_RAW[verified]}."
                    )

                LOGGER.info(
                    "RIV4835 Program 01 verified write register=0x1159 raw=%d decoded=%s",
                    verified,
                    OUTPUT_PRIORITY_BY_RAW[verified],
                )
                return verified
        finally:
            try:
                if client is not None and device is not None and session is not None:
                    await _close_session_if_needed(client, device, session)
            finally:
                coordinator._connection_in_progress = False


async def async_read_output_priority(coordinator: Any) -> int:
    """Return authoritative Program 01 readback from register 0x1159."""
    return await _run_transaction(coordinator, target=None)


async def async_write_output_priority(coordinator: Any, target: int) -> int:
    """Write UTI/SBU and return only the independently verified readback."""
    return await _run_transaction(coordinator, target=target)
