"""Bridge Communication Hub battery telemetry into Home Assistant-safe state."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from inspect import signature
from typing import Any

HubFactory = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class RenogyHubBatteryState:
    """Validated read-only telemetry for one Communication Hub battery."""

    slave_id: int
    battery_voltage: float | None
    battery_current: float | None
    battery_power: float | None
    battery_remaining_capacity: float | None
    battery_capacity: float | None
    battery_percentage: float | None
    cell_voltages: tuple[float, ...] | None = None
    cell_voltage_min: float | None = None
    cell_voltage_max: float | None = None
    cell_voltage_delta: float | None = None
    cell_voltage_max_cell_number: int | None = None
    available: bool = True

    def as_dict(self) -> dict[str, float | int | None]:
        """Return only fields independently validated against Hub hardware."""
        return {
            "slave_id": self.slave_id,
            "battery_voltage": self.battery_voltage,
            "battery_current": self.battery_current,
            "battery_power": self.battery_power,
            "battery_remaining_capacity": self.battery_remaining_capacity,
            "battery_capacity": self.battery_capacity,
            "battery_percentage": self.battery_percentage,
        }


@dataclass(frozen=True, slots=True)
class RenogyHubBankState:
    """Derived telemetry for batteries currently communicating through the Hub."""

    communicating_battery_count: int
    discovered_battery_count: int
    battery_current: float | None
    battery_power: float | None
    battery_remaining_capacity: float | None
    battery_capacity: float | None
    battery_percentage: float | None
    battery_percentage_min: float | None = None
    battery_percentage_min_slave_id: int | None = None
    battery_percentage_max: float | None = None
    battery_percentage_max_slave_id: int | None = None
    battery_percentage_spread: float | None = None
    battery_voltage_min: float | None = None
    battery_voltage_min_slave_id: int | None = None
    battery_voltage_max: float | None = None
    battery_voltage_max_slave_id: int | None = None
    battery_voltage_spread: float | None = None
    battery_current_spread: float | None = None
    cell_telemetry_battery_count: int = 0
    cell_voltage_max: float | None = None
    cell_voltage_max_slave_id: int | None = None
    cell_voltage_max_cell_number: int | None = None
    cell_voltage_delta_max: float | None = None
    cell_voltage_delta_max_slave_id: int | None = None

    def as_dict(self) -> dict[str, float | int | None]:
        """Return primary communicating-bank aggregate telemetry."""
        return {
            "communicating_battery_count": self.communicating_battery_count,
            "discovered_battery_count": self.discovered_battery_count,
            "battery_current": self.battery_current,
            "battery_power": self.battery_power,
            "battery_remaining_capacity": self.battery_remaining_capacity,
            "battery_capacity": self.battery_capacity,
            "battery_percentage": self.battery_percentage,
        }


@dataclass(frozen=True, slots=True)
class _HubRange:
    """Complete min/max/spread telemetry for one battery field."""

    minimum: float | None
    minimum_slave_id: int | None
    maximum: float | None
    maximum_slave_id: int | None
    spread: float | None


def hub_battery_identifier(address: str, slave_id: int) -> str:
    """Return a stable logical device identifier below one physical BLE address."""
    return f"{address}:hub:{slave_id:02X}"


def hub_bank_identifier(address: str) -> str:
    """Return a stable logical identifier for the communicating battery bank."""
    return f"{address}:hub:bank"


class RenogyHubBatteryManager:
    """Cache read-only logical battery state from a Renogy Communication Hub."""

    def __init__(
        self,
        client: Any,
        *,
        hub_factory: HubFactory | None = None,
    ) -> None:
        """Initialize the Hub state manager."""
        factory = hub_factory or self._load_hub_factory()
        self._hub = factory(client)
        self._supports_cell_status = _supports_include_cell_status(self._hub)
        self._batteries: dict[int, RenogyHubBatteryState] = {}
        self.last_error: Exception | None = None

    @staticmethod
    def _load_hub_factory() -> HubFactory:
        """Load Hub support lazily so older renogy-ble releases still import."""
        hub_module = importlib.import_module("renogy_ble.hub")
        return hub_module.RenogyCommunicationHub

    @property
    def batteries(self) -> tuple[RenogyHubBatteryState, ...]:
        """Return cached batteries ordered by Modbus slave ID."""
        return tuple(self._batteries[key] for key in sorted(self._batteries))

    @property
    def bank(self) -> RenogyHubBankState | None:
        """Return aggregates for batteries that are currently communicating."""
        batteries = self.batteries
        if not batteries:
            return None

        communicating = tuple(battery for battery in batteries if battery.available)
        remaining_capacity = _sum_complete(
            communicating, "battery_remaining_capacity", precision=3
        )
        nominal_capacity = _sum_complete(communicating, "battery_capacity", precision=3)
        percentage_range = _range_complete(
            communicating, "battery_percentage", precision=1
        )
        voltage_range = _range_complete(communicating, "battery_voltage", precision=1)
        current_range = _range_complete(communicating, "battery_current", precision=2)
        cell_telemetry = tuple(
            battery
            for battery in communicating
            if battery.cell_voltage_max is not None
            and battery.cell_voltage_delta is not None
        )
        cell_telemetry_complete = bool(communicating) and len(cell_telemetry) == len(
            communicating
        )

        highest_cell_battery: RenogyHubBatteryState | None = None
        largest_delta_battery: RenogyHubBatteryState | None = None
        if cell_telemetry_complete:
            highest_cell_battery = max(
                cell_telemetry,
                key=lambda battery: float(battery.cell_voltage_max or 0.0),
            )
            largest_delta_battery = max(
                cell_telemetry,
                key=lambda battery: float(battery.cell_voltage_delta or 0.0),
            )

        percentage: float | None = None
        if (
            remaining_capacity is not None
            and nominal_capacity is not None
            and nominal_capacity > 0
        ):
            percentage = round(remaining_capacity / nominal_capacity * 100, 1)

        return RenogyHubBankState(
            communicating_battery_count=len(communicating),
            discovered_battery_count=len(batteries),
            battery_current=_sum_complete(
                communicating, "battery_current", precision=2
            ),
            battery_power=_sum_complete(communicating, "battery_power", precision=3),
            battery_remaining_capacity=remaining_capacity,
            battery_capacity=nominal_capacity,
            battery_percentage=percentage,
            battery_percentage_min=percentage_range.minimum,
            battery_percentage_min_slave_id=percentage_range.minimum_slave_id,
            battery_percentage_max=percentage_range.maximum,
            battery_percentage_max_slave_id=percentage_range.maximum_slave_id,
            battery_percentage_spread=percentage_range.spread,
            battery_voltage_min=voltage_range.minimum,
            battery_voltage_min_slave_id=voltage_range.minimum_slave_id,
            battery_voltage_max=voltage_range.maximum,
            battery_voltage_max_slave_id=voltage_range.maximum_slave_id,
            battery_voltage_spread=voltage_range.spread,
            battery_current_spread=current_range.spread,
            cell_telemetry_battery_count=len(cell_telemetry),
            cell_voltage_max=(
                highest_cell_battery.cell_voltage_max
                if highest_cell_battery is not None
                else None
            ),
            cell_voltage_max_slave_id=(
                highest_cell_battery.slave_id
                if highest_cell_battery is not None
                else None
            ),
            cell_voltage_max_cell_number=(
                highest_cell_battery.cell_voltage_max_cell_number
                if highest_cell_battery is not None
                else None
            ),
            cell_voltage_delta_max=(
                largest_delta_battery.cell_voltage_delta
                if largest_delta_battery is not None
                else None
            ),
            cell_voltage_delta_max_slave_id=(
                largest_delta_battery.slave_id
                if largest_delta_battery is not None
                else None
            ),
        )

    def get_battery(self, slave_id: int) -> RenogyHubBatteryState | None:
        """Return cached state for one Hub battery."""
        return self._batteries.get(slave_id)

    def mark_unavailable(self, error: Exception) -> None:
        """Retain cached telemetry while marking every Hub battery unavailable."""
        self.last_error = error
        for slave_id, state in tuple(self._batteries.items()):
            self._batteries[slave_id] = replace(state, available=False)

    async def async_update(self, device: Any, *, rediscover: bool = False) -> bool:
        """Read Hub batteries and refresh the validated logical-device cache."""
        read_kwargs: dict[str, bool] = {"rediscover": rediscover}
        if self._supports_cell_status:
            read_kwargs["include_cell_status"] = True
        result = await self._hub.read_batteries(device, **read_kwargs)
        self.last_error = result.error

        seen_slave_ids: set[int] = set()
        for battery in result.batteries:
            state = self._state_from_battery(battery)
            seen_slave_ids.add(state.slave_id)
            self._batteries[state.slave_id] = state

        for slave_id, state in tuple(self._batteries.items()):
            if slave_id not in seen_slave_ids:
                self._batteries[slave_id] = replace(state, available=False)

        return bool(result.success)

    @staticmethod
    def _state_from_battery(battery: Any) -> RenogyHubBatteryState:
        """Copy only independently validated fields from a library Hub battery."""
        data = battery.parsed_data
        cell_voltages = _optional_float_tuple(data.get("cell_voltages"))
        cell_voltage_max = _optional_float(data.get("cell_voltage_max"))
        if cell_voltage_max is None and cell_voltages:
            cell_voltage_max = max(cell_voltages)

        cell_voltage_min = _optional_float(data.get("cell_voltage_min"))
        if cell_voltage_min is None and cell_voltages:
            cell_voltage_min = min(cell_voltages)

        cell_voltage_delta = _optional_float(data.get("cell_voltage_delta"))
        if (
            cell_voltage_delta is None
            and cell_voltage_min is not None
            and cell_voltage_max is not None
        ):
            cell_voltage_delta = round(cell_voltage_max - cell_voltage_min, 3)

        max_cell_number: int | None = None
        if cell_voltages:
            max_cell_number = max(
                range(len(cell_voltages)),
                key=cell_voltages.__getitem__,
            ) + 1

        return RenogyHubBatteryState(
            slave_id=int(battery.slave_id),
            battery_voltage=_optional_float(data.get("battery_voltage")),
            battery_current=_optional_float(data.get("battery_current")),
            battery_power=_optional_float(data.get("battery_power")),
            battery_remaining_capacity=_optional_float(
                data.get("battery_remaining_capacity")
            ),
            battery_capacity=_optional_float(data.get("battery_capacity")),
            battery_percentage=_optional_float(data.get("battery_percentage")),
            cell_voltages=cell_voltages,
            cell_voltage_min=cell_voltage_min,
            cell_voltage_max=cell_voltage_max,
            cell_voltage_delta=cell_voltage_delta,
            cell_voltage_max_cell_number=max_cell_number,
        )


def _sum_complete(
    batteries: tuple[RenogyHubBatteryState, ...],
    field: str,
    *,
    precision: int,
) -> float | None:
    """Sum a field only when every communicating battery has a valid value."""
    if not batteries:
        return None

    values: list[float] = []
    for battery in batteries:
        value = getattr(battery, field)
        if value is None:
            return None
        values.append(float(value))
    return round(sum(values), precision)


def _range_complete(
    batteries: tuple[RenogyHubBatteryState, ...],
    field: str,
    *,
    precision: int,
) -> _HubRange:
    """Return min/max/spread only when every communicating battery has the field."""
    if not batteries:
        return _HubRange(None, None, None, None, None)

    values: list[tuple[RenogyHubBatteryState, float]] = []
    for battery in batteries:
        value = getattr(battery, field)
        if value is None:
            return _HubRange(None, None, None, None, None)
        values.append((battery, float(value)))

    minimum_battery, minimum_value = min(values, key=lambda item: item[1])
    maximum_battery, maximum_value = max(values, key=lambda item: item[1])
    return _HubRange(
        minimum=round(minimum_value, precision),
        minimum_slave_id=minimum_battery.slave_id,
        maximum=round(maximum_value, precision),
        maximum_slave_id=maximum_battery.slave_id,
        spread=round(maximum_value - minimum_value, precision),
    )


def _supports_include_cell_status(hub: Any) -> bool:
    """Return whether the installed library supports optional Hub cell reads."""
    try:
        return "include_cell_status" in signature(hub.read_batteries).parameters
    except TypeError, ValueError:
        return False


def _optional_float_tuple(value: Any) -> tuple[float, ...] | None:
    """Return a non-empty tuple of numeric cell voltages, otherwise None."""
    if not isinstance(value, (list, tuple)) or not value:
        return None

    values: list[float] = []
    try:
        for item in value:
            values.append(float(item))
    except TypeError, ValueError:
        return None
    return tuple(values)


def _optional_float(value: Any) -> float | None:
    """Return a float for numeric Hub telemetry, otherwise None."""
    if value is None:
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None
