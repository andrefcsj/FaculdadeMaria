"""Stable domain contracts for option opportunities.

The contracts in this module are intentionally independent from Flask,
persistence, concrete market-data providers, and network libraries.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ..errors import EngineContractError


_OPTION_TYPES = frozenset({"PUT", "CALL"})
_MARKET_DATA_FIELDS = (
    "spot_price",
    "strike",
    "premium",
    "bid",
    "ask",
    "volume",
    "trades",
    "liquidity",
    "implied_volatility",
    "timestamp",
    "source",
    "data_confidence",
)


def _raise_contract_error(message: str, *, field: str | None = None, value: Any = None) -> None:
    details = {}
    if field is not None:
        details["field"] = field
    if value is not None:
        details["value"] = repr(value)
    raise EngineContractError(message, details=details)


def _validate_decimal(
    name: str,
    value: Decimal | None,
    *,
    strictly_positive: bool = False,
    non_negative: bool = False,
) -> None:
    if value is None:
        return
    if not isinstance(value, Decimal):
        _raise_contract_error(f"{name} must be a Decimal or None", field=name, value=value)
    if not value.is_finite():
        _raise_contract_error(f"{name} must be finite", field=name, value=value)
    if strictly_positive and value <= 0:
        _raise_contract_error(f"{name} must be greater than zero", field=name, value=value)
    if non_negative and value < 0:
        _raise_contract_error(f"{name} cannot be negative", field=name, value=value)


@dataclass(frozen=True, slots=True)
class OptionOpportunity:
    """Canonical normalized input contract for an option opportunity.

    Missing optional market fields remain ``None``. Explicit zero values remain
    zero, allowing callers to distinguish absence from a reported zero.
    """

    asset: str
    option_code: str
    option_type: str
    expiry: date
    spot_price: Decimal | None = None
    strike: Decimal | None = None
    premium: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    volume: int | None = None
    trades: int | None = None
    liquidity: Decimal | None = None
    implied_volatility: Decimal | None = None
    timestamp: datetime | None = None
    source: str | None = None
    data_confidence: Decimal | None = None

    def __post_init__(self) -> None:
        asset = self.asset.strip() if isinstance(self.asset, str) else self.asset
        option_code = self.option_code.strip() if isinstance(self.option_code, str) else self.option_code
        option_type = self.option_type.strip().upper() if isinstance(self.option_type, str) else self.option_type
        source = self.source.strip() if isinstance(self.source, str) else self.source

        if not isinstance(asset, str) or not asset:
            _raise_contract_error("asset must be a non-empty string", field="asset", value=self.asset)
        if not isinstance(option_code, str) or not option_code:
            _raise_contract_error(
                "option_code must be a non-empty string", field="option_code", value=self.option_code
            )
        if option_type not in _OPTION_TYPES:
            _raise_contract_error(
                "option_type must be PUT or CALL", field="option_type", value=self.option_type
            )
        if isinstance(self.expiry, datetime) or not isinstance(self.expiry, date):
            _raise_contract_error("expiry must be a date", field="expiry", value=self.expiry)

        object.__setattr__(self, "asset", asset)
        object.__setattr__(self, "option_code", option_code)
        object.__setattr__(self, "option_type", option_type)
        object.__setattr__(self, "source", source)

        _validate_decimal("spot_price", self.spot_price, strictly_positive=True)
        _validate_decimal("strike", self.strike, strictly_positive=True)
        _validate_decimal("premium", self.premium, non_negative=True)
        _validate_decimal("bid", self.bid, non_negative=True)
        _validate_decimal("ask", self.ask, non_negative=True)
        _validate_decimal("liquidity", self.liquidity, non_negative=True)
        _validate_decimal("implied_volatility", self.implied_volatility, non_negative=True)
        _validate_decimal("data_confidence", self.data_confidence, non_negative=True)

        for name in ("volume", "trades"):
            value = getattr(self, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int):
                _raise_contract_error(f"{name} must be an integer or None", field=name, value=value)
            if value < 0:
                _raise_contract_error(f"{name} cannot be negative", field=name, value=value)

        if self.bid is not None and self.ask is not None and self.ask < self.bid:
            _raise_contract_error("ask cannot be lower than bid", field="ask", value=self.ask)

        if self.timestamp is not None:
            if not isinstance(self.timestamp, datetime):
                _raise_contract_error(
                    "timestamp must be a datetime or None", field="timestamp", value=self.timestamp
                )
            if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
                _raise_contract_error(
                    "timestamp must include timezone information", field="timestamp", value=self.timestamp
                )

        if source is not None and not source:
            _raise_contract_error("source cannot be blank", field="source", value=self.source)

        if self.data_confidence is not None and not (Decimal("0") <= self.data_confidence <= Decimal("1")):
            _raise_contract_error(
                "data_confidence must be between 0 and 1",
                field="data_confidence",
                value=self.data_confidence,
            )

    def missing_fields(self) -> tuple[str, ...]:
        """Return optional market fields that were not supplied."""

        return tuple(name for name in _MARKET_DATA_FIELDS if getattr(self, name) is None)

    def require_fields(self, *names: str) -> None:
        """Raise a structured contract error when required values are absent."""

        valid_names = {field.name for field in fields(self)}
        unknown = tuple(name for name in names if name not in valid_names)
        if unknown:
            raise EngineContractError(
                "Unknown contract fields requested",
                details={"unknown_fields": list(unknown)},
            )
        missing = tuple(name for name in names if getattr(self, name) is None)
        if missing:
            raise EngineContractError(
                "Required opportunity fields are missing",
                details={"missing_fields": list(missing)},
            )
