"""Radar service for the first visual Radar screen.

This service intentionally uses controlled demonstration data. It does not fetch
quotes, access persistence, or call external providers. The goal is to expose the
Decision Engine output in a UI-ready shape while the real provider layer is not
implemented yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from engine import (
    AssetQualityPolicy,
    AssetQualityProfile,
    ExplainableScoreConfig,
    OptionOpportunity,
    PutMetricAssumptions,
    RankingConfig,
    SafetyFilterConfig,
    assess_asset_quality,
    calculate_put_metrics,
    calculate_put_score,
    evaluate_put_safety,
    evaluate_put_strategy,
    rank_put_opportunities,
)


@dataclass(frozen=True, slots=True)
class RadarCard:
    position: int
    asset: str
    option_code: str
    status: str
    headline: str
    reason: str
    score: int | None
    gross_roi_pct: str
    discount_pct: str
    net_price: str
    capital: str
    dte: int


def _money(value: Decimal) -> str:
    text = f"R$ {value.quantize(Decimal('0.01'))}"
    return text.replace(".", ",")


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%".replace(".", ",")


def _demo_inputs(as_of: date) -> tuple[tuple[OptionOpportunity, AssetQualityProfile], ...]:
    expiry = as_of + timedelta(days=35)
    return (
        (
            OptionOpportunity(
                asset="BBAS3",
                option_code="BBASQ270",
                option_type="PUT",
                expiry=expiry,
                spot_price=Decimal("28.50"),
                strike=Decimal("27.00"),
                premium=Decimal("1.10"),
                bid=Decimal("1.05"),
                ask=Decimal("1.15"),
                liquidity=Decimal("32000"),
                data_confidence=Decimal("0.92"),
                source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="BBAS3",
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=Decimal("0.88"),
                data_confidence=Decimal("0.90"),
                positive_notes=("Ativo aprovado para eventual exercício",),
                source="demo_controlado",
            ),
        ),
        (
            OptionOpportunity(
                asset="ITSA4",
                option_code="ITSAQ100",
                option_type="PUT",
                expiry=expiry,
                spot_price=Decimal("10.80"),
                strike=Decimal("10.00"),
                premium=Decimal("0.40"),
                bid=Decimal("0.36"),
                ask=Decimal("0.44"),
                liquidity=Decimal("18000"),
                data_confidence=Decimal("0.84"),
                source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="ITSA4",
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=Decimal("0.68"),
                data_confidence=Decimal("0.82"),
                warnings=("Qualidade aceitável, mas ainda abaixo do nível ideal",),
                positive_notes=("Preço líquido oferece desconto relevante",),
                source="demo_controlado",
            ),
        ),
        (
            OptionOpportunity(
                asset="ALTO3",
                option_code="ALTOQ150",
                option_type="PUT",
                expiry=expiry,
                spot_price=Decimal("16.00"),
                strike=Decimal("15.00"),
                premium=Decimal("1.20"),
                bid=Decimal("1.12"),
                ask=Decimal("1.28"),
                liquidity=Decimal("26000"),
                data_confidence=Decimal("0.76"),
                source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="ALTO3",
                assignment_eligible=False,
                long_term_suitable=False,
                quality_score=Decimal("0.42"),
                data_confidence=Decimal("0.70"),
                blocking_events=("Ativo não aprovado para exercício",),
                source="demo_controlado",
            ),
        ),
    )


def build_demo_radar(as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Build UI-ready Radar cards from controlled demonstration opportunities."""

    as_of = as_of or date.today()
    safety_config = SafetyFilterConfig(
        min_liquidity=Decimal("10000"),
        max_spread_pct=Decimal("0.25"),
        min_gross_roi=Decimal("0.04"),
        min_days_to_expiry=15,
        max_days_to_expiry=60,
    )
    asset_policy = AssetQualityPolicy(
        min_quality_score=Decimal("0.60"),
        attention_quality_score=Decimal("0.75"),
        min_data_confidence=Decimal("0.50"),
    )
    score_config = ExplainableScoreConfig(target_gross_roi=Decimal("0.04"))

    ranking_items = []
    indexed = {}
    for opportunity, profile in _demo_inputs(as_of):
        assumptions = PutMetricAssumptions(as_of_date=as_of, contract_size=100, costs_total=Decimal("0"))
        metrics = calculate_put_metrics(opportunity, assumptions)
        safety = evaluate_put_safety(opportunity, metrics, safety_config)
        quality = assess_asset_quality(profile, asset_policy)
        strategy = evaluate_put_strategy(opportunity, metrics, safety, quality)
        score = calculate_put_score(strategy, metrics, quality, score_config)
        opportunity_id = opportunity.option_code
        ranking_items.append((opportunity_id, strategy, score))
        indexed[opportunity_id] = (opportunity, metrics)

    ranked = rank_put_opportunities(ranking_items, RankingConfig(include_blocked=True))
    cards: list[RadarCard] = []
    for item in ranked:
        opportunity, metrics = indexed[item.opportunity_id]
        cards.append(
            RadarCard(
                position=item.position,
                asset=opportunity.asset,
                option_code=opportunity.option_code,
                status=item.summary.status,
                headline=item.summary.headline,
                reason=item.summary.reason,
                score=item.summary.score,
                gross_roi_pct=_pct(metrics.gross_roi),
                discount_pct=_pct(metrics.discount_to_market),
                net_price=_money(metrics.net_acquisition_price),
                capital=_money(metrics.nominal_committed_capital),
                dte=metrics.days_to_expiry,
            )
        )
    return tuple(cards)
