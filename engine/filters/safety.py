"""Deterministic safety filters for option opportunities.

These filters do not calculate Score, ranking, asset quality, or final trading
recommendations. They only expose explainable pass/attention/fail checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from ..core.contracts import OptionOpportunity
from ..errors import EngineContractError
from ..metrics.options import PutMetrics


PASSED = "passed"
ATTENTION = "attention"
FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SafetyFilterConfig:
    """Explicit thresholds for deterministic safety checks."""

    required_fields: tuple[str, ...] = ("spot_price", "strike", "premium")
    min_liquidity: Decimal | None = None
    max_spread_pct: Decimal | None = None
    min_gross_roi: Decimal | None = None
    min_days_to_expiry: int | None = None
    max_days_to_expiry: int | None = None
    allow_itm_put: bool = False


@dataclass(frozen=True, slots=True)
class SafetyCheck:
    code: str
    status: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SafetyEvaluation:
    status: str
    checks: tuple[SafetyCheck, ...]

    @property
    def failed_checks(self) -> tuple[SafetyCheck, ...]:
        return tuple(check for check in self.checks if check.status == FAILED)

    @property
    def attention_checks(self) -> tuple[SafetyCheck, ...]:
        return tuple(check for check in self.checks if check.status == ATTENTION)

    @property
    def passed(self) -> bool:
        return self.status == PASSED


def _validate_decimal_threshold(value: Decimal | None, *, field: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        raise EngineContractError(f"{field} must be Decimal or None", details={"field": field})
    if not value.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    if value < 0:
        raise EngineContractError(f"{field} cannot be negative", details={"field": field})
    return value


def _validate_day_threshold(value: int | None, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise EngineContractError(f"{field} must be a non-negative integer or None", details={"field": field})
    return value


def _check_threshold_order(config: SafetyFilterConfig) -> None:
    min_days = _validate_day_threshold(config.min_days_to_expiry, field="min_days_to_expiry")
    max_days = _validate_day_threshold(config.max_days_to_expiry, field="max_days_to_expiry")
    if min_days is not None and max_days is not None and min_days > max_days:
        raise EngineContractError("min_days_to_expiry cannot be greater than max_days_to_expiry")


def _spread_pct(opportunity: OptionOpportunity) -> Decimal | None:
    if opportunity.bid is None or opportunity.ask is None:
        return None
    if opportunity.bid == 0 and opportunity.ask == 0:
        return Decimal("0")
    midpoint = (opportunity.bid + opportunity.ask) / Decimal("2")
    if midpoint <= 0:
        return None
    return (opportunity.ask - opportunity.bid) / midpoint


def evaluate_put_safety(
    opportunity: OptionOpportunity,
    metrics: PutMetrics | None = None,
    config: SafetyFilterConfig | None = None,
) -> SafetyEvaluation:
    """Evaluate deterministic safety checks for a PUT opportunity."""

    if not isinstance(opportunity, OptionOpportunity):
        raise EngineContractError("opportunity must be an OptionOpportunity")
    if opportunity.option_type != "PUT":
        raise EngineContractError("safety filters currently require option_type PUT")
    if metrics is not None and not isinstance(metrics, PutMetrics):
        raise EngineContractError("metrics must be PutMetrics or None")

    config = config or SafetyFilterConfig()
    if not isinstance(config, SafetyFilterConfig):
        raise EngineContractError("config must be SafetyFilterConfig")

    _validate_decimal_threshold(config.min_liquidity, field="min_liquidity")
    _validate_decimal_threshold(config.max_spread_pct, field="max_spread_pct")
    _validate_decimal_threshold(config.min_gross_roi, field="min_gross_roi")
    _check_threshold_order(config)

    checks: list[SafetyCheck] = []

    missing = tuple(field for field in config.required_fields if getattr(opportunity, field, None) is None)
    if missing:
        checks.append(
            SafetyCheck(
                code="missing_required_data",
                status=FAILED,
                message="Required data is missing",
                details={"missing_fields": list(missing)},
            )
        )
    else:
        checks.append(
            SafetyCheck(
                code="required_data",
                status=PASSED,
                message="Required data is present",
                details={"required_fields": list(config.required_fields)},
            )
        )

    if config.min_liquidity is not None:
        if opportunity.liquidity is None:
            checks.append(
                SafetyCheck(
                    code="liquidity_missing",
                    status=ATTENTION,
                    message="Liquidity data is missing",
                )
            )
        elif opportunity.liquidity < config.min_liquidity:
            checks.append(
                SafetyCheck(
                    code="liquidity_below_minimum",
                    status=FAILED,
                    message="Liquidity is below the configured minimum",
                    details={"liquidity": str(opportunity.liquidity), "minimum": str(config.min_liquidity)},
                )
            )
        else:
            checks.append(
                SafetyCheck(
                    code="liquidity_minimum",
                    status=PASSED,
                    message="Liquidity meets the configured minimum",
                    details={"liquidity": str(opportunity.liquidity)},
                )
            )

    if config.max_spread_pct is not None:
        spread_pct = _spread_pct(opportunity)
        if spread_pct is None:
            checks.append(
                SafetyCheck(
                    code="spread_missing",
                    status=ATTENTION,
                    message="Bid/ask spread cannot be evaluated",
                )
            )
        elif spread_pct > config.max_spread_pct:
            checks.append(
                SafetyCheck(
                    code="spread_above_maximum",
                    status=FAILED,
                    message="Bid/ask spread is above the configured maximum",
                    details={"spread_pct": str(spread_pct), "maximum": str(config.max_spread_pct)},
                )
            )
        else:
            checks.append(
                SafetyCheck(
                    code="spread_maximum",
                    status=PASSED,
                    message="Bid/ask spread is within the configured maximum",
                    details={"spread_pct": str(spread_pct)},
                )
            )

    if not config.allow_itm_put and opportunity.spot_price is not None and opportunity.strike is not None:
        if opportunity.strike > opportunity.spot_price:
            checks.append(
                SafetyCheck(
                    code="put_strike_above_spot",
                    status=FAILED,
                    message="PUT strike is above spot and is not allowed by the current safety config",
                    details={"spot_price": str(opportunity.spot_price), "strike": str(opportunity.strike)},
                )
            )
        else:
            checks.append(
                SafetyCheck(
                    code="put_strike_position",
                    status=PASSED,
                    message="PUT strike is not above spot",
                )
            )

    if metrics is None:
        if (
            config.min_gross_roi is not None
            or config.min_days_to_expiry is not None
            or config.max_days_to_expiry is not None
        ):
            checks.append(
                SafetyCheck(
                    code="metrics_missing",
                    status=ATTENTION,
                    message="PUT metrics are required for ROI and DTE safety checks",
                )
            )
    else:
        if config.min_gross_roi is not None:
            if metrics.gross_roi < config.min_gross_roi:
                checks.append(
                    SafetyCheck(
                        code="gross_roi_below_minimum",
                        status=FAILED,
                        message="Gross ROI is below the configured minimum",
                        details={"gross_roi": str(metrics.gross_roi), "minimum": str(config.min_gross_roi)},
                    )
                )
            else:
                checks.append(
                    SafetyCheck(
                        code="gross_roi_minimum",
                        status=PASSED,
                        message="Gross ROI meets the configured minimum",
                        details={"gross_roi": str(metrics.gross_roi)},
                    )
                )

        min_days = config.min_days_to_expiry
        max_days = config.max_days_to_expiry
        if min_days is not None and metrics.days_to_expiry < min_days:
            checks.append(
                SafetyCheck(
                    code="dte_below_minimum",
                    status=FAILED,
                    message="DTE is below the configured minimum",
                    details={"days_to_expiry": metrics.days_to_expiry, "minimum": min_days},
                )
            )
        elif min_days is not None:
            checks.append(
                SafetyCheck(
                    code="dte_minimum",
                    status=PASSED,
                    message="DTE meets the configured minimum",
                    details={"days_to_expiry": metrics.days_to_expiry},
                )
            )

        if max_days is not None and metrics.days_to_expiry > max_days:
            checks.append(
                SafetyCheck(
                    code="dte_above_maximum",
                    status=FAILED,
                    message="DTE is above the configured maximum",
                    details={"days_to_expiry": metrics.days_to_expiry, "maximum": max_days},
                )
            )
        elif max_days is not None:
            checks.append(
                SafetyCheck(
                    code="dte_maximum",
                    status=PASSED,
                    message="DTE is within the configured maximum",
                    details={"days_to_expiry": metrics.days_to_expiry},
                )
            )

    if any(check.status == FAILED for check in checks):
        status = FAILED
    elif any(check.status == ATTENTION for check in checks):
        status = ATTENTION
    else:
        status = PASSED

    return SafetyEvaluation(status=status, checks=tuple(checks))
