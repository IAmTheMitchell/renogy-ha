"""Regression tests for RIV4835CSH1S Program 01 BLE readback timing."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from tests.test_ble import _load_ble_module
from tests.test_number import _load_select_module, _riv_output_priority_entity


def _entity_with_write_result(acknowledged: bool = True):
    """Build a Select whose BLE write and subsequent polls can be simulated."""
    select, coordinator, entity = _riv_output_priority_entity()
    coordinator.async_write_setting = AsyncMock(return_value=acknowledged)
    coordinator.async_request_refresh = AsyncMock()
    return select, coordinator, entity


def test_immediately_confirmed_write_does_not_wait_or_retry() -> None:
    """A confirmed write must not introduce extra polling latency."""
    select, coordinator, entity = _entity_with_write_result()

    async def write_setting(key: str, option: str) -> bool:
        assert key == "output_priority"
        coordinator.data = {"output_priority": option}
        coordinator.output_priority_readback = (
            coordinator.output_priority_readback[0] + 1,
            option,
        )
        return True

    coordinator.async_write_setting = AsyncMock(side_effect=write_setting)

    with patch.object(select.asyncio, "sleep", new_callable=AsyncMock) as sleep:
        asyncio.run(entity.async_select_option("UTI"))

    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "UTI")
    coordinator.async_request_refresh.assert_not_awaited()
    sleep.assert_not_awaited()
    assert entity.current_option == "UTI"
    entity.async_write_ha_state.assert_called_once()


def test_acknowledged_write_waits_for_delayed_readback() -> None:
    """A delayed authoritative poll must not produce a false failure."""
    select, coordinator, entity = _entity_with_write_result()
    polls = 0

    async def refresh() -> None:
        nonlocal polls
        polls += 1
        if polls == 2:
            coordinator.data = {"output_priority": "UTI"}
            coordinator.output_priority_readback = (polls, "UTI")

    coordinator.async_request_refresh = AsyncMock(side_effect=refresh)

    with patch.object(select.asyncio, "sleep", new_callable=AsyncMock) as sleep:
        asyncio.run(entity.async_select_option("UTI"))

    assert sleep.await_args_list == [call(2.0), call(4.0)]
    assert coordinator.async_request_refresh.await_count == 2
    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "UTI")
    assert entity.current_option == "UTI"
    entity.async_write_ha_state.assert_called_once()


def test_missing_acknowledgment_can_be_confirmed_by_later_poll() -> None:
    """A missing FC06 acknowledgment is not a second write or automatic failure."""
    select, coordinator, entity = _entity_with_write_result(False)
    polls = 0

    async def refresh() -> None:
        nonlocal polls
        polls += 1
        if polls == 3:
            coordinator.data = {"output_priority": "UTI"}
            coordinator.output_priority_readback = (polls, "UTI")

    coordinator.async_request_refresh = AsyncMock(side_effect=refresh)

    with (
        patch.object(select.asyncio, "sleep", new_callable=AsyncMock) as sleep,
        patch.object(select.LOGGER, "warning") as warning,
    ):
        asyncio.run(entity.async_select_option("UTI"))

    assert sleep.await_args_list == [call(2.0), call(4.0), call(6.0)]
    assert coordinator.async_request_refresh.await_count == 3
    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "UTI")
    assert entity.current_option == "UTI"
    entity.async_write_ha_state.assert_called_once()
    warning.assert_called_once()


@pytest.mark.parametrize(
    ("acknowledged", "message"),
    [
        (True, "Output priority readback did not confirm UTI"),
        (False, "Failed to write output priority: UTI"),
    ],
)
def test_unconfirmed_write_still_fails_without_optimistic_state(
    acknowledged: bool, message: str
) -> None:
    """An unconfirmed mode must keep the prior polled value and report an error."""
    select, coordinator, entity = _entity_with_write_result(acknowledged)

    with (
        patch.object(select.asyncio, "sleep", new_callable=AsyncMock) as sleep,
        patch.object(select.LOGGER, "warning") as warning,
    ):
        with pytest.raises(select.HomeAssistantError, match=message):
            asyncio.run(entity.async_select_option("UTI"))

    assert sleep.await_args_list == [
        call(2.0),
        call(4.0),
        call(6.0),
        call(8.0),
    ]
    assert coordinator.async_request_refresh.await_count == 4
    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "UTI")
    assert entity.current_option == "SBU"
    entity.async_write_ha_state.assert_not_called()
    warning.assert_not_called()


def test_confirmation_reads_the_device_polled_value() -> None:
    """Real device parsed_data takes precedence over a stale coordinator snapshot."""
    select, coordinator, entity = _entity_with_write_result(False)
    device = MagicMock(parsed_data={"output_priority": "SBU"})
    coordinator.device = device
    coordinator.data = {"output_priority": "SBU"}

    async def refresh() -> None:
        device.parsed_data = {"output_priority": "UTI"}
        coordinator.output_priority_readback = (1, "UTI")

    coordinator.async_request_refresh = AsyncMock(side_effect=refresh)

    with patch.object(select.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(entity.async_select_option("UTI"))

    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "UTI")
    assert entity.current_option == "UTI"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.parametrize("acknowledged", [True, False])
def test_cached_matching_mode_is_not_fresh_confirmation(acknowledged: bool) -> None:
    """A failed or skipped refresh cannot confirm a cached matching mode."""
    select, coordinator, entity = _entity_with_write_result(acknowledged)

    with (
        patch.object(select.asyncio, "sleep", new_callable=AsyncMock),
        pytest.raises(select.HomeAssistantError),
    ):
        asyncio.run(entity.async_select_option("SBU"))

    coordinator.async_write_setting.assert_awaited_once_with("output_priority", "SBU")
    assert coordinator.async_request_refresh.await_count == 4
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.parametrize("acknowledged", [True, False])
@pytest.mark.parametrize("initial", ["SBU", "UTI"])
def test_real_coordinator_confirms_completed_poll(
    acknowledged: bool, initial: str
) -> None:
    """Exercise the Select and coordinator together with delayed device data."""
    ble = _load_ble_module()
    coordinator = ble.RenogyActiveBluetoothCoordinator(
        hass=MagicMock(),
        logger=MagicMock(),
        address="AA:BB:CC:DD:EE:FF",
        device_type="inverter",
        model_hint="RIV4835CSH1S",
    )
    coordinator.device = MagicMock(parsed_data={"output_priority": initial})
    coordinator.data = {"output_priority": initial}
    coordinator._service_info_for_operation = MagicMock(return_value=None)
    coordinator._can_use_cached_device_without_service_info = MagicMock(
        return_value=True
    )
    coordinator._ble_client.write_setting = AsyncMock(
        return_value=MagicMock(success=acknowledged)
    )
    polls = 0

    async def read_device(device):
        nonlocal polls
        polls += 1
        device.parsed_data = {"output_priority": initial if polls == 1 else "UTI"}
        return MagicMock(success=True, error=None)

    coordinator._ble_client.read_device = AsyncMock(side_effect=read_device)
    select = _load_select_module()
    entity = select.RenogyOutputPrioritySelect(
        coordinator, coordinator.device, select.RIV_SELECT_ENTITIES[0], "inverter"
    )
    entity.async_write_ha_state = MagicMock()

    with patch.object(select.asyncio, "sleep", new_callable=AsyncMock):
        asyncio.run(entity.async_select_option("UTI"))

    coordinator._ble_client.write_setting.assert_awaited_once_with(
        coordinator.device, "output_priority", "UTI"
    )
    assert coordinator.output_priority_readback == (polls, "UTI")
    assert polls == (1 if initial == "UTI" else 2)
    assert entity.current_option == "UTI"
    entity.async_write_ha_state.assert_called_once()


def test_failed_partial_poll_cannot_confirm_after_successful_mismatch() -> None:
    """A partial failed poll cannot borrow the revision of an earlier read."""
    select, coordinator, entity = _entity_with_write_result(False)
    device = MagicMock(parsed_data={"output_priority": "SBU"})
    coordinator.device = device
    polls = 0

    async def refresh():
        nonlocal polls
        polls += 1
        if polls == 1:
            coordinator.output_priority_readback = (1, "SBU")
        else:
            device.parsed_data = {"output_priority": "UTI"}

    coordinator.async_request_refresh = AsyncMock(side_effect=refresh)
    with (
        patch.object(select.asyncio, "sleep", new_callable=AsyncMock),
        pytest.raises(select.HomeAssistantError),
    ):
        asyncio.run(entity.async_select_option("UTI"))

    assert polls == 4
    entity.async_write_ha_state.assert_not_called()
