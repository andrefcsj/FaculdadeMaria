"""Pure, auditable metrics for systematic PUT selling."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ..core.contracts import OptionOpportunity
from ..errors import EngineContractError


def _as_decimal(value: Any, *, field: str, allow_none: bool = True) -> Decimal | None:
    if value is None:
        if allow_none:
            return None
        raise EngineContractError(f"{field} is required", details={"field": field})
    if isinstance(value, bool):
        raise EngineContractError(f"{field} must be numeric", details={"field": field})
    try:
        normalized = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise EngineContractError(
            f"{field} must be numeric", details={"field": field, "value": repr(value)}
        ) from None
    if not normalized.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    return normalized


@dataclass(frozen=True, slots=True)
class PutMetricAssumptions:
    """Explicit calculation assumptions.

    ``contract_size`` is a caller-supplied multiplier. The default of 1 means
    metrics are calculated per underlying unit; no B3 lot size is invented.
    ``costs_total`` is the explicit total cost for the evaluated position.
    ``committed_capital`` and ``real_margin`` are total monetary amounts.
    """

    as_of_date: date
    contract_size: int = 1
    costs_total: Decimal | None = None
    committed_capital: Decimal | None = None
    real_margin: Decimal | None = None
    annualization_days: int = 365

    def __post_init__(self) -> None:
        if isinstance(self.as_of_date, datetime) or not isinstance(self.as_of_date, date):
            raise EngineContractError("as_of_date must be a date")
        if isinstance(self.contract_size, bool) or not isinstance(self.contract_size, int) or self.contract_size <= 0:
            raise EngineContractError(
                "contract_size must be a positive integer",
                details={"field": "contract_size", "value": repr(self.contract_size)},
            )
        if (
            isinstance(self.annualization_days, bool)
            or not isinstance(self.annualization_days, int)
            or self.annualization_days <= 0
        ):
            raise EngineContractError(
                "annualization_days must be a positive integer",
                details={"field": "annualization_days", "value": repr(self.annualization_days)},
            )

        for field_name in ("costs_total", "committed_capital", "real_margin"):
            value = getattr(self, field_name)
            normalized = _as_decimal(value, field=field_name)
            if normalized is not None and normalized < 0:
                raise EngineContractError(
                    f"{field_name} cannot be negative",
                    details={"field": field_name, "value": repr(value)},
                )
            if field_name in {"committed_capital", "real_margin"} and normalized == 0:
                raise EngineContractError(
                    f"{field_name} must be greater than zero when supplied",
                    details={"field": field_name, "value": repr(value)},
                )
            object.__setattr__(self, field_name, normalized)


@dataclass(frozen=True, slots=True)
class PutMetrics:
    """Calculated PUT metrics expressed as Decimal ratios and monetary values."""

    net_acquisition_price: Decimal
    discount_to_market: Decimal
    gross_roi: Decimal
    net_roi: Decimal | None
    annualized_roi: Decimal | None
    net_annualized_roi: Decimal | None
    strike_distance_pct: Decimal
    days_to_expiry: int
    return_per_day: Decimal | None
    gross_premium_income: Decimal
    net_premium_income: Decimal | None
    nominal_committed_capital: Decimal
    capital_efficiency: Decimal
    return_on_margin: Decimal | None
    capital_basis: str
    annualization_method: str
    annualization_days: int
    contract_size: int


def calculate_put_metrics(
    opportunity: OptionOpportunity,
    assumptions: PutMetricAssumptions,
) -> PutMetrics:
    """Calculate deterministic PUT metrics using explicit assumptions.

    Conventions:
    - gross ROI uses nominal cash-secured capital (strike * contract_size);
    - annualization is simple: ROI * annualization_days / DTE;
    - net ROI exists only when explicit total costs are supplied;
    - capital efficiency uses explicit committed capital when supplied,
      otherwise nominal cash-secured capital;
    - return on margin exists only when real margin is supplied.
    """

    if not isinstance(opportunity, OptionOpportunity):
        raise EngineContractError("opportunity must be an OptionOpportunity")
    if not isinstance(assumptions, PutMetricAssumptions):
        raise EngineContractError("assumptions must be PutMetricAssumptions")
    if opportunity.option_type != "PUT":
        raise EngineContractError(
            "PUT metrics require option_type PUT",
            details={"option_type": opportunity.option_type},
        )

    opportunity.require_fields("spot_price", "strike", "premium")
    spot_price = opportunity.spot_price
    strike = opportunity.strike
    premium = opportunity.premium
    assert spot_price is not None and strike is not None and premium is not None

    dte = (opportunity.expiry - assumptions.as_of_date).days
    if dte < 0:
        raise EngineContractError(
            "expiry cannot be before as_of_date",
            details={
                "expiry": opportunity.expiry.isoformat(),
                "as_of_date": assumptions.as_of_date.isoformat(),
            },
        )

    multiplier = Decimal(assumptions.contract_size)
    gross_premium_income = premium * multiplier
    nominal_committed_capital = strike * multiplier
    if nominal_committed_capital <= 0:
        raise EngineContractError("Nominal committed capital must be greater than zero")

    net_acquisition_price = strike - premium
    discount_to_market = (spot_price - net_acquisition_price) / spot_price
    gross_roi = gross_premium_income / nominal_committed_capital
    strike_distance_pct = (spot_price - strike) / spot_price

    net_premium_income = None
    net_roi = None
    if assumptions.costs_total is not None:
        net_premium_income = gross_premium_income - assumptions.costs_total
        net_roi = net_premium_income / nominal_committed_capital

    annualized_roi = None
    net_annualized_roi = None
    return_per_day = None
    if dte > 0:
        day_count = Decimal(assumptions.annualization_days)
        dte_decimal = Decimal(dte)
        annualized_roi = gross_roi * day_count / dte_decimal
        return_per_day = gross_roi / dte_decimal
        if net_roi is not None:
            net_annualized_roi = net_roi * day_count / dte_decimal

    if assumptions.committed_capital is not None:
        effective_capital = assumptions.committed_capital
        capital_basis = "explicit_committed_capital"
    else:
        effective_capital = nominal_committed_capital
        capital_basis = "nominal_cash_secured"
    capital_efficiency = gross_premium_income / effective_capital

    return_on_margin = None
    if assumptions.real_margin is not None:
        return_on_margin = gross_premium_income / assumptions.real_margin

    return PutMetrics(
        net_acquisition_price=net_acquisition_price,
        discount_to_market=discount_to_market,
        gross_roi=gross_roi,
        net_roi=net_roi,
        annualized_roi=annualized_roi,
        net_annualized_roi=net_annualized_roi,
        strike_distance_pct=strike_distance_pct,
        days_to_expiry=dte,
        return_per_day=return_per_day,
        gross_premium_income=gross_premium_income,
        net_premium_income=net_premium_income,
        nominal_committed_capital=nominal_committed_capital,
        capital_efficiency=capital_efficiency,
        return_on_margin=return_on_margin,
        capital_basis=capital_basis,
        annualization_method="simple",
        annualization_days=assumptions.annualization_days,
        contract_size=assumptions.contract_size,
    )
