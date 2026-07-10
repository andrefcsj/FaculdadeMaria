"""Explainable Score IA for systematic PUT selling.

The score is intentionally deterministic and auditable. It does not fetch data,
rank opportunities, or create final trading recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..asset.quality import (
    ATTENTION as ASSET_ATTENTION,
    FAILED as ASSET_FAILED,
    INSUFFICIENT_DATA as ASSET_INSUFFICIENT_DATA,
    PASSED as ASSET_PASSED,
    AssetQualityAssessment,
)
from ..errors import EngineContractError
from ..filters.safety import ATTENTION as SAFETY_ATTENTION, FAILED as SAFETY_FAILED, PASSED as SAFETY_PASSED
from ..metrics.options import PutMetrics
from ..strategy.put import (
    ELIGIBLE,
    INELIGIBLE,
    INSUFFICIENT_DATA,
    WATCHLIST,
    PutStrategyEvaluation,
)

DEFAULT_TARGET_GROSS_ROI = Decimal("0.04")
SCORE_READY = "score_ready"
SCORE_WATCHLIST = "score_watchlist"
SCORE_BLOCKED = "score_blocked"
SCORE_INSUFFICIENT_DATA = "score_insufficient_data"


def _validate_ratio(value: Decimal, *, field: str, strictly_positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal):
        raise EngineContractError(f"{field} must be Decimal", details={"field": field, "value": repr(value)})
    if not value.is_finite():
        raise EngineContractError(f"{field} must be finite", details={"field": field})
    if strictly_positive and value <= 0:
        raise EngineContractError(f"{field} must be greater than zero", details={"field": field})
    if not strictly_positive and value < 0:
        raise EngineContractError(f"{field} cannot be negative", details={"field": field})
    return value


@dataclass(frozen=True, slots=True)
class ExplainableScoreConfig:
    """Explicit Score IA configuration.

    The default gross ROI target is 4%, defined by the Product Owner for the
    whole system. Weights are ratios and are normalized at calculation time.
    """

    target_gross_roi: Decimal = DEFAULT_TARGET_GROSS_ROI
    target_discount_to_market: Decimal = Decimal("0.05")
    target_capital_efficiency: Decimal = DEFAULT_TARGET_GROSS_ROI
    weight_asset_quality: Decimal = Decimal("0.30")
    weight_safety: Decimal = Decimal("0.25")
    weight_roi: Decimal = Decimal("0.20")
    weight_price: Decimal = Decimal("0.15")
    weight_capital_efficiency: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        for field_name in (
            "target_gross_roi",
            "target_discount_to_market",
            "target_capital_efficiency",
        ):
            object.__setattr__(
                self,
                field_name,
                _validate_ratio(getattr(self, field_name), field=field_name, strictly_positive=True),
            )

        total_weight = Decimal("0")
        for field_name in (
            "weight_asset_quality",
            "weight_safety",
            "weight_roi",
            "weight_price",
            "weight_capital_efficiency",
        ):
            weight = _validate_ratio(getattr(self, field_name), field=field_name)
            object.__setattr__(self, field_name, weight)
            total_weight += weight
        if total_weight <= 0:
            raise EngineContractError("At least one score weight must be greater than zero")

    @property
    def total_weight(self) -> Decimal:
        return (
            self.weight_asset_quality
            + self.weight_safety
            + self.weight_roi
            + self.weight_price
            + self.weight_capital_efficiency
        )


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    code: str
    label: str
    weight: Decimal
    factor: Decimal
    points: Decimal
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScoreEvaluation:
    score: Decimal
    status: str
    components: tuple[ScoreComponent, ...]
    penalties: tuple[str, ...]
    data_confidence: Decimal | None
    target_gross_roi: Decimal
    explanation: str

    @property
    def score_int(self) -> int:
        return int(self.score.to_integral_value())


def _clamp_ratio(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0")
    if value > 1:
        return Decimal("1")
    return value


def _target_factor(value: Decimal, target: Decimal) -> Decimal:
    return _clamp_ratio(value / target)


def _asset_quality_factor(asset_quality: AssetQualityAssessment) -> tuple[Decimal, str]:
    if asset_quality.status == ASSET_FAILED:
        return Decimal("0"), "Asset quality failed"
    if asset_quality.status == ASSET_INSUFFICIENT_DATA:
        return Decimal("0"), "Asset quality data is insufficient"
    if asset_quality.quality_score is not None:
        if asset_quality.status == ASSET_ATTENTION:
            return _clamp_ratio(asset_quality.quality_score), "Asset quality requires attention"
        return _clamp_ratio(asset_quality.quality_score), "Asset quality score supplied"
    if asset_quality.status == ASSET_ATTENTION:
        return Decimal("0.65"), "Asset quality requires attention"
    if asset_quality.status == ASSET_PASSED:
        return Decimal("1"), "Asset quality passed"
    return Decimal("0"), "Asset quality unavailable"


def _safety_factor(status: str) -> tuple[Decimal, str]:
    if status == SAFETY_PASSED:
        return Decimal("1"), "Safety filters passed"
    if status == SAFETY_ATTENTION:
        return Decimal("0.55"), "Safety filters require attention"
    if status == SAFETY_FAILED:
        return Decimal("0"), "Safety filters failed"
    return Decimal("0"), "Safety status unavailable"


def _normalized_weight(weight: Decimal, total: Decimal) -> Decimal:
    return weight / total


def _component(
    *,
    code: str,
    label: str,
    raw_weight: Decimal,
    total_weight: Decimal,
    factor: Decimal,
    message: str,
    details: dict[str, Any] | None = None,
) -> ScoreComponent:
    normalized = _normalized_weight(raw_weight, total_weight)
    points = normalized * Decimal("100") * _clamp_ratio(factor)
    return ScoreComponent(
        code=code,
        label=label,
        weight=normalized,
        factor=_clamp_ratio(factor),
        points=points,
        message=message,
        details=details or {},
    )


def calculate_put_score(
    strategy: PutStrategyEvaluation,
    metrics: PutMetrics,
    asset_quality: AssetQualityAssessment,
    config: ExplainableScoreConfig | None = None,
) -> ScoreEvaluation:
    """Calculate an explainable Score IA for a PUT opportunity.

    The score is blocked at zero when the strategy is ineligible or has
    insufficient asset data. High ROI never overrides failed gates.
    """

    if not isinstance(strategy, PutStrategyEvaluation):
        raise EngineContractError("strategy must be PutStrategyEvaluation")
    if not isinstance(metrics, PutMetrics):
        raise EngineContractError("metrics must be PutMetrics")
    if not isinstance(asset_quality, AssetQualityAssessment):
        raise EngineContractError("asset_quality must be AssetQualityAssessment")

    config = config or ExplainableScoreConfig()
    if not isinstance(config, ExplainableScoreConfig):
        raise EngineContractError("config must be ExplainableScoreConfig")

    total_weight = config.total_weight
    components: list[ScoreComponent] = []
    penalties: list[str] = []

    asset_factor, asset_message = _asset_quality_factor(asset_quality)
    safety_factor, safety_message = _safety_factor(strategy.safety_status)
    roi_factor = _target_factor(metrics.gross_roi, config.target_gross_roi)
    price_factor = _target_factor(metrics.discount_to_market, config.target_discount_to_market)
    capital_factor = _target_factor(metrics.capital_efficiency, config.target_capital_efficiency)

    components.append(
        _component(
            code="asset_quality",
            label="Qualidade do ativo",
            raw_weight=config.weight_asset_quality,
            total_weight=total_weight,
            factor=asset_factor,
            message=asset_message,
            details={"asset_quality_status": asset_quality.status, "quality_score": str(asset_quality.quality_score)},
        )
    )
    components.append(
        _component(
            code="safety",
            label="Segurança",
            raw_weight=config.weight_safety,
            total_weight=total_weight,
            factor=safety_factor,
            message=safety_message,
            details={"safety_status": strategy.safety_status},
        )
    )
    components.append(
        _component(
            code="gross_roi_vs_target",
            label="ROI bruto vs alvo",
            raw_weight=config.weight_roi,
            total_weight=total_weight,
            factor=roi_factor,
            message="ROI compared with the configured target",
            details={"gross_roi": str(metrics.gross_roi), "target_gross_roi": str(config.target_gross_roi)},
        )
    )
    components.append(
        _component(
            code="net_price_discount",
            label="Preço líquido / desconto",
            raw_weight=config.weight_price,
            total_weight=total_weight,
            factor=price_factor,
            message="Net acquisition discount compared with target",
            details={"discount_to_market": str(metrics.discount_to_market), "target_discount": str(config.target_discount_to_market)},
        )
    )
    components.append(
        _component(
            code="capital_efficiency",
            label="Eficiência do capital",
            raw_weight=config.weight_capital_efficiency,
            total_weight=total_weight,
            factor=capital_factor,
            message="Capital efficiency compared with target",
            details={"capital_efficiency": str(metrics.capital_efficiency), "target": str(config.target_capital_efficiency)},
        )
    )

    raw_score = sum((component.points for component in components), Decimal("0"))

    if strategy.status == INELIGIBLE:
        penalties.append("Strategy gates failed: score cannot rescue an ineligible PUT")
        return ScoreEvaluation(
            score=Decimal("0"),
            status=SCORE_BLOCKED,
            components=tuple(components),
            penalties=tuple(penalties),
            data_confidence=strategy.data_confidence,
            target_gross_roi=config.target_gross_roi,
            explanation="Score blocked because the PUT is ineligible under strategy gates.",
        )

    if strategy.status == INSUFFICIENT_DATA:
        penalties.append("Asset or strategy data is insufficient for a valid Score IA")
        return ScoreEvaluation(
            score=Decimal("0"),
            status=SCORE_INSUFFICIENT_DATA,
            components=tuple(components),
            penalties=tuple(penalties),
            data_confidence=strategy.data_confidence,
            target_gross_roi=config.target_gross_roi,
            explanation="Score unavailable because required strategy data is insufficient.",
        )

    if strategy.status == WATCHLIST:
        status = SCORE_WATCHLIST
        explanation = "Score calculated, but the PUT remains on watchlist due to attention points."
    elif strategy.status == ELIGIBLE:
        status = SCORE_READY
        explanation = "Score calculated for an initially eligible PUT opportunity."
    else:
        status = SCORE_INSUFFICIENT_DATA
        explanation = "Score status could not be finalized from the strategy state."

    return ScoreEvaluation(
        score=_clamp_ratio(raw_score / Decimal("100")) * Decimal("100"),
        status=status,
        components=tuple(components),
        penalties=tuple(penalties),
        data_confidence=strategy.data_confidence,
        target_gross_roi=config.target_gross_roi,
        explanation=explanation,
    )
