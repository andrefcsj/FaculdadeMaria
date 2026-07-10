"""Pure normalization helpers for provider-independent market snapshots."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from ..core.contracts import OptionOpportunity
from ..errors import EngineContractError
from .snapshot import NormalizedMarketSnapshot


_NUMERIC_FIELDS = (
    "spot_price",
    "strike",
    "premium",
    "bid",
    "ask",
    "liquidity",
    "implied_volatility",
    "data_confidence",
)
_INTEGER_FIELDS = ("volume", "trades")


def _error(message: str, *, field: str, value: Any = None) -> EngineContractError:
    details = {"field": field}
    if value is not None:
        details["value"] = repr(value)
    return EngineContractError(message, details=details)


def normalize_decimal(value: Any, *, field: str, allow_none: bool = True) -> Decimal | None:
    """Normalize common numeric inputs without converting absence into zero.

    Strings accept decimal point or decimal comma. When both separators are
    present, the last separator is treated as the decimal separator.
    """

    if value is None:
        if allow_none:
            return None
        raise _error(f"{field} is required", field=field)
    if isinstance(value, bool):
        raise _error(f"{field} must be numeric", field=field, value=value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            if allow_none:
                return None
            raise _error(f"{field} is required", field=field, value=value)
        text = text.replace(" ", "")
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")
        value = text
    try:
        normalized = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise _error(f"{field} must be numeric", field=field, value=value) from None
    if not normalized.is_finite():
        raise _error(f"{field} must be finite", field=field, value=value)
    return normalized


def normalize_integer(value: Any, *, field: str, allow_none: bool = True) -> int | None:
    if value is None:
        if allow_none:
            return None
        raise _error(f"{field} is required", field=field)
    if isinstance(value, bool):
        raise _error(f"{field} must be an integer", field=field, value=value)
    decimal_value = normalize_decimal(value, field=field, allow_none=allow_none)
    if decimal_value is None:
        return None
    integral = decimal_value.to_integral_value()
    if decimal_value != integral:
        raise _error(f"{field} must be an integer", field=field, value=value)
    return int(integral)


def normalize_date(value: Any, *, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for parser in (
            lambda item: date.fromisoformat(item),
            lambda item: datetime.strptime(item, "%d/%m/%Y").date(),
        ):
            try:
                return parser(text)
            except ValueError:
                continue
    raise _error(f"{field} must be a valid date", field=field, value=value)


def normalize_timestamp(value: Any, *, field: str = "timestamp") -> datetime | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        normalized = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            normalized = datetime.fromisoformat(text)
        except ValueError:
            raise _error(f"{field} must be an ISO-8601 datetime", field=field, value=value) from None
    else:
        raise _error(f"{field} must be a datetime", field=field, value=value)
    if normalized.tzinfo is None or normalized.utcoffset() is None:
        raise _error(f"{field} must include timezone information", field=field, value=value)
    return normalized.astimezone(timezone.utc)


def normalize_market_snapshot(raw: Mapping[str, Any]) -> NormalizedMarketSnapshot:
    """Normalize canonical provider-independent fields into a stable snapshot."""

    if not isinstance(raw, Mapping):
        raise EngineContractError("Market snapshot must be a mapping")

    normalized: dict[str, Any] = dict(raw)
    for field in _NUMERIC_FIELDS:
        normalized[field] = normalize_decimal(raw.get(field), field=field)
    for field in _INTEGER_FIELDS:
        normalized[field] = normalize_integer(raw.get(field), field=field)

    normalized["expiry"] = normalize_date(raw.get("expiry"), field="expiry")
    normalized["timestamp"] = normalize_timestamp(raw.get("timestamp"))

    opportunity = OptionOpportunity(
        asset=raw.get("asset"),
        option_code=raw.get("option_code"),
        option_type=raw.get("option_type"),
        expiry=normalized["expiry"],
        spot_price=normalized["spot_price"],
        strike=normalized["strike"],
        premium=normalized["premium"],
        bid=normalized["bid"],
        ask=normalized["ask"],
        volume=normalized["volume"],
        trades=normalized["trades"],
        liquidity=normalized["liquidity"],
        implied_volatility=normalized["implied_volatility"],
        timestamp=normalized["timestamp"],
        source=raw.get("source"),
        data_confidence=normalized["data_confidence"],
    )
    return NormalizedMarketSnapshot.from_opportunity(opportunity)
