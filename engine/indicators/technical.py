"""Pure technical indicators for the Decision Engine.

The functions here are deterministic and intentionally independent from Flask,
persistence, providers, CSV, databases, and network libraries.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, Sequence

from ..errors import EngineContractError


def _to_decimal(value, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise EngineContractError(f"{field} must be numeric", details={"field": field})
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise EngineContractError(
            f"{field} must be numeric", details={"field": field, "value": repr(value)}
        ) from None
    if not result.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    return result


def _decimal_series(values: Iterable, *, field: str) -> tuple[Decimal, ...]:
    if values is None:
        raise EngineContractError(f"{field} is required", details={"field": field})
    try:
        result = tuple(_to_decimal(item, field=field) for item in values)
    except TypeError:
        raise EngineContractError(f"{field} must be iterable", details={"field": field}) from None
    return result


def _positive_period(period: int, *, field: str = "period") -> int:
    if isinstance(period, bool) or not isinstance(period, int) or period <= 0:
        raise EngineContractError(
            f"{field} must be a positive integer", details={"field": field, "value": repr(period)}
        )
    return period


@dataclass(frozen=True, slots=True)
class BollingerBands:
    middle: Decimal
    upper: Decimal
    lower: Decimal
    standard_deviation: Decimal
    period: int
    deviations: Decimal


def simple_moving_average(values: Sequence, period: int) -> Decimal | None:
    """Return the simple moving average for the last ``period`` values."""

    period = _positive_period(period)
    series = _decimal_series(values, field="values")
    if len(series) < period:
        return None
    window = series[-period:]
    return sum(window, Decimal("0")) / Decimal(period)


def moving_average_21(values: Sequence) -> Decimal | None:
    return simple_moving_average(values, 21)


def moving_average_200(values: Sequence) -> Decimal | None:
    return simple_moving_average(values, 200)


def relative_strength_index(values: Sequence, period: int = 14) -> Decimal | None:
    """Calculate RSI/IFR using the average gain/loss over the last period.

    Returns ``None`` when history is insufficient. A flat window returns 50.
    """

    period = _positive_period(period)
    series = _decimal_series(values, field="values")
    if len(series) < period + 1:
        return None

    window = series[-(period + 1):]
    gains = []
    losses = []
    for previous, current in zip(window, window[1:]):
        change = current - previous
        if change > 0:
            gains.append(change)
            losses.append(Decimal("0"))
        elif change < 0:
            gains.append(Decimal("0"))
            losses.append(abs(change))
        else:
            gains.append(Decimal("0"))
            losses.append(Decimal("0"))

    average_gain = sum(gains, Decimal("0")) / Decimal(period)
    average_loss = sum(losses, Decimal("0")) / Decimal(period)

    if average_gain == 0 and average_loss == 0:
        return Decimal("50")
    if average_loss == 0:
        return Decimal("100")
    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def bollinger_bands(values: Sequence, period: int = 20, deviations=Decimal("2")) -> BollingerBands | None:
    """Return Bollinger Bands using population standard deviation."""

    period = _positive_period(period)
    deviation_multiplier = _to_decimal(deviations, field="deviations")
    if deviation_multiplier < 0:
        raise EngineContractError("deviations cannot be negative", details={"field": "deviations"})
    series = _decimal_series(values, field="values")
    if len(series) < period:
        return None

    window = series[-period:]
    middle = sum(window, Decimal("0")) / Decimal(period)
    variance = sum((item - middle) ** 2 for item in window) / Decimal(period)
    standard_deviation = variance.sqrt()
    spread = standard_deviation * deviation_multiplier
    return BollingerBands(
        middle=middle,
        upper=middle + spread,
        lower=middle - spread,
        standard_deviation=standard_deviation,
        period=period,
        deviations=deviation_multiplier,
    )


def _validate_ohlc(highs: Sequence, lows: Sequence, closes: Sequence) -> tuple[tuple[Decimal, ...], tuple[Decimal, ...], tuple[Decimal, ...]]:
    high_values = _decimal_series(highs, field="highs")
    low_values = _decimal_series(lows, field="lows")
    close_values = _decimal_series(closes, field="closes")
    if not (len(high_values) == len(low_values) == len(close_values)):
        raise EngineContractError("highs, lows and closes must have the same length")
    for high, low in zip(high_values, low_values):
        if high < low:
            raise EngineContractError("high cannot be lower than low")
    return high_values, low_values, close_values


def true_range(high, low, previous_close) -> Decimal:
    high_value = _to_decimal(high, field="high")
    low_value = _to_decimal(low, field="low")
    previous_close_value = _to_decimal(previous_close, field="previous_close")
    if high_value < low_value:
        raise EngineContractError("high cannot be lower than low")
    return max(
        high_value - low_value,
        abs(high_value - previous_close_value),
        abs(low_value - previous_close_value),
    )


def average_true_range(highs: Sequence, lows: Sequence, closes: Sequence, period: int = 14) -> Decimal | None:
    """Return ATR over the last ``period`` true ranges."""

    period = _positive_period(period)
    high_values, low_values, close_values = _validate_ohlc(highs, lows, closes)
    if len(close_values) < period + 1:
        return None

    ranges = []
    start = len(close_values) - period
    for index in range(start, len(close_values)):
        ranges.append(true_range(high_values[index], low_values[index], close_values[index - 1]))
    return sum(ranges, Decimal("0")) / Decimal(period)


def historical_volatility(
    closes: Sequence,
    period: int = 21,
    annualization_days: int = 252,
) -> Decimal | None:
    """Return annualized historical volatility from simple returns.

    The function intentionally uses simple returns to remain transparent and
    Decimal-based. The chosen convention is part of the output contract of this
    Sprint and can be replaced later only by an explicit Sprint decision.
    """

    period = _positive_period(period)
    annualization_days = _positive_period(annualization_days, field="annualization_days")
    close_values = _decimal_series(closes, field="closes")
    if len(close_values) < period + 1:
        return None

    window = close_values[-(period + 1):]
    returns = []
    for previous, current in zip(window, window[1:]):
        if previous <= 0:
            raise EngineContractError("close values must be greater than zero")
        returns.append((current / previous) - Decimal("1"))

    mean = sum(returns, Decimal("0")) / Decimal(period)
    variance = sum((item - mean) ** 2 for item in returns) / Decimal(period)
    daily_volatility = variance.sqrt()
    return daily_volatility * Decimal(annualization_days).sqrt()


def strike_distance_in_atr(spot_price, strike, atr) -> Decimal | None:
    """Return absolute distance between spot and strike measured in ATR units."""

    if atr is None:
        return None
    spot = _to_decimal(spot_price, field="spot_price")
    strike_value = _to_decimal(strike, field="strike")
    atr_value = _to_decimal(atr, field="atr")
    if spot <= 0:
        raise EngineContractError("spot_price must be greater than zero")
    if strike_value <= 0:
        raise EngineContractError("strike must be greater than zero")
    if atr_value <= 0:
        return None
    return abs(spot - strike_value) / atr_value
