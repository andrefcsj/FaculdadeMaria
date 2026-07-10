"""Initial PUT strategy evaluator.

This module combines explicit PUT metrics, safety filters, and asset quality.
It still does not create Score IA, ranking, or final portfolio recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..asset.quality import (
    ATTENTION as ASSET_ATTENTION,
    FAILED as ASSET_FAILED,
    INSUFFICIENT_DATA as ASSET_INSUFFICIENT_DATA,
    AssetQualityAssessment,
)
from ..core.contracts import OptionOpportunity
from ..errors import EngineContractError
from ..filters.safety import ATTENTION, FAILED, PASSED, SafetyEvaluation
from ..metrics.options import PutMetrics

ELIGIBLE = "eligible"
WATCHLIST = "watchlist"
INELIGIBLE = "ineligible"
INSUFFICIENT_DATA = "insufficient_data"


def _validate_ratio(value: Decimal | None, *, field: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, Decimal):
        raise EngineContractError(f"{field} must be Decimal or None", details={"field": field, "value": repr(value)})
    if not value.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    if value < 0 or value > 1:
        raise EngineContractError(f"{field} must be between 0 and 1", details={"field": field, "value": repr(value)})
    return value


@dataclass(frozen=True, slots=True)
class PutStrategyConfig:
    min_discount_to_market: Decimal | None = None
    min_capital_efficiency: Decimal | None = None
    max_position_pct: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "min_discount_to_market",
            _validate_ratio(self.min_discount_to_market, field="min_discount_to_market"),
        )
        object.__setattr__(
            self,
            "min_capital_efficiency",
            _validate_ratio(self.min_capital_efficiency, field="min_capital_efficiency"),
        )
        object.__setattr__(self, "max_position_pct", _validate_ratio(self.max_position_pct, field="max_position_pct"))


@dataclass(frozen=True, slots=True)
class StrategyCheck:
    code: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PutStrategyEvaluation:
    status: str
    checks: tuple[StrategyCheck, ...]
    positive_factors: tuple[str, ...]
    attention_points: tuple[str, ...]
    blockers: tuple[str, ...]
    conclusion: str
    net_acquisition_price: Decimal
    gross_roi: Decimal
    discount_to_market: Decimal
    capital_efficiency: Decimal
    safety_status: str
    asset_quality_status: str
    data_confidence: Decimal | None

    @property
    def eligible(self) -> bool:
        return self.status == ELIGIBLE


def _combine_confidence(opportunity: OptionOpportunity, asset: AssetQualityAssessment) -> Decimal | None:
    values = [value for value in (opportunity.data_confidence, asset.data_confidence) if value is not None]
    if not values:
        return None
    return min(values)


def _status_from_inputs(
    safety: SafetyEvaluation,
    asset: AssetQualityAssessment,
    checks: list[StrategyCheck],
) -> str:
    if safety.status == FAILED or asset.status == ASSET_FAILED or any(check.status == FAILED for check in checks):
        return INELIGIBLE
    if asset.status == ASSET_INSUFFICIENT_DATA:
        return INSUFFICIENT_DATA
    if safety.status == ATTENTION or asset.status == ASSET_ATTENTION or any(check.status == ATTENTION for check in checks):
        return WATCHLIST
    return ELIGIBLE


def evaluate_put_strategy(
    opportunity: OptionOpportunity,
    metrics: PutMetrics,
    safety: SafetyEvaluation,
    asset_quality: AssetQualityAssessment,
    config: PutStrategyConfig | None = None,
) -> PutStrategyEvaluation:
    """Evaluate a PUT opportunity without Score/ranking.

    High premium or ROI never overrides failed safety or failed asset quality.
    """

    if not isinstance(opportunity, OptionOpportunity):
        raise EngineContractError("opportunity must be OptionOpportunity")
    if opportunity.option_type != "PUT":
        raise EngineContractError("PUT strategy evaluation requires option_type PUT")
    if not isinstance(metrics, PutMetrics):
        raise EngineContractError("metrics must be PutMetrics")
    if not isinstance(safety, SafetyEvaluation):
        raise EngineContractError("safety must be SafetyEvaluation")
    if not isinstance(asset_quality, AssetQualityAssessment):
        raise EngineContractError("asset_quality must be AssetQualityAssessment")
    if asset_quality.asset != opportunity.asset:
        raise EngineContractError(
            "asset_quality asset must match opportunity asset",
            details={"opportunity_asset": opportunity.asset, "asset_quality_asset": asset_quality.asset},
        )

    config = config or PutStrategyConfig()
    if not isinstance(config, PutStrategyConfig):
        raise EngineContractError("config must be PutStrategyConfig")

    checks: list[StrategyCheck] = []
    positives: list[str] = []
    attention: list[str] = []
    blockers: list[str] = []

    if safety.status == FAILED:
        blockers.append("Safety filters failed")
        checks.append(
            StrategyCheck(
                code="safety_failed",
                status=FAILED,
                message="Safety filters failed",
                details={"failed_checks": [check.code for check in safety.failed_checks]},
            )
        )
    elif safety.status == ATTENTION:
        attention.append("Safety filters require attention")
        checks.append(StrategyCheck(code="safety_attention", status=ATTENTION, message="Safety filters require attention"))
    else:
        positives.append("Safety filters passed")
        checks.append(StrategyCheck(code="safety_passed", status=PASSED, message="Safety filters passed"))

    if asset_quality.status == ASSET_FAILED:
        blockers.extend(asset_quality.blockers or ("Asset quality failed",))
        checks.append(
            StrategyCheck(
                code="asset_quality_failed",
                status=FAILED,
                message="Asset quality failed",
                details={"blockers": list(asset_quality.blockers)},
            )
        )
    elif asset_quality.status == ASSET_INSUFFICIENT_DATA:
        attention.append("Asset quality has insufficient data")
        checks.append(
            StrategyCheck(
                code="asset_quality_insufficient_data",
                status=INSUFFICIENT_DATA,
                message="Asset quality has insufficient data",
            )
        )
    elif asset_quality.status == ASSET_ATTENTION:
        attention.extend(asset_quality.warnings or ("Asset quality requires attention",))
        checks.append(
            StrategyCheck(
                code="asset_quality_attention",
                status=ATTENTION,
                message="Asset quality requires attention",
                details={"warnings": list(asset_quality.warnings)},
            )
        )
    else:
        positives.extend(asset_quality.positive_factors or ("Asset quality passed",))
        checks.append(StrategyCheck(code="asset_quality_passed", status=PASSED, message="Asset quality passed"))

    if config.min_discount_to_market is not None:
        if metrics.discount_to_market < config.min_discount_to_market:
            attention.append("Net acquisition discount below preferred minimum")
            checks.append(
                StrategyCheck(
                    code="discount_below_minimum",
                    status=ATTENTION,
                    message="Net acquisition discount is below the configured minimum",
                    details={"discount_to_market": str(metrics.discount_to_market), "minimum": str(config.min_discount_to_market)},
                )
            )
        else:
            positives.append("Net acquisition discount meets policy")
            checks.append(StrategyCheck(code="discount_minimum", status=PASSED, message="Net acquisition discount meets policy"))

    if config.min_capital_efficiency is not None:
        if metrics.capital_efficiency < config.min_capital_efficiency:
            attention.append("Capital efficiency below preferred minimum")
            checks.append(
                StrategyCheck(
                    code="capital_efficiency_below_minimum",
                    status=ATTENTION,
                    message="Capital efficiency is below the configured minimum",
                    details={"capital_efficiency": str(metrics.capital_efficiency), "minimum": str(config.min_capital_efficiency)},
                )
            )
        else:
            positives.append("Capital efficiency meets policy")
            checks.append(StrategyCheck(code="capital_efficiency_minimum", status=PASSED, message="Capital efficiency meets policy"))

    if config.max_position_pct is not None and metrics.capital_basis != "explicit_committed_capital":
        attention.append("Explicit committed capital not supplied for position sizing")
        checks.append(
            StrategyCheck(
                code="position_size_unavailable",
                status=ATTENTION,
                message="Position sizing needs explicit committed capital",
            )
        )

    status = _status_from_inputs(safety, asset_quality, checks)
    confidence = _combine_confidence(opportunity, asset_quality)

    if status == ELIGIBLE:
        conclusion = "PUT opportunity is initially eligible under the current strategy gates."
    elif status == WATCHLIST:
        conclusion = "PUT opportunity is not rejected, but requires attention before execution."
    elif status == INSUFFICIENT_DATA:
        conclusion = "PUT opportunity cannot be considered eligible because asset quality data is insufficient."
    else:
        conclusion = "PUT opportunity is ineligible under the current strategy gates."

    return PutStrategyEvaluation(
        status=status,
        checks=tuple(checks),
        positive_factors=tuple(dict.fromkeys(positives)),
        attention_points=tuple(dict.fromkeys(attention)),
        blockers=tuple(dict.fromkeys(blockers)),
        conclusion=conclusion,
        net_acquisition_price=metrics.net_acquisition_price,
        gross_roi=metrics.gross_roi,
        discount_to_market=metrics.discount_to_market,
        capital_efficiency=metrics.capital_efficiency,
        safety_status=safety.status,
        asset_quality_status=asset_quality.status,
        data_confidence=confidence,
    )
