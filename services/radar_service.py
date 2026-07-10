"""Radar service for the visual Radar screen.

The service can build Radar cards from controlled demonstration data or from
already-loaded real operations supplied by the Flask app. It does not fetch
quotes, access persistence directly, or call external providers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

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
from engine.errors import DecisionEngineError


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
    roi_concept: str
    roi_concept_class: str
    source: str = "demo"


def _money(value: Decimal) -> str:
    text = f"R$ {value.quantize(Decimal('0.01'))}"
    return text.replace(".", ",")


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%".replace(".", ",")


def _roi_concept(gross_roi: Decimal) -> tuple[str, str]:
    """Classify only ROI attractiveness, not the full operation quality."""

    if gross_roi >= Decimal("0.03"):
        return "Excelente", "excellent"
    if gross_roi >= Decimal("0.015"):
        return "Bom", "good"
    if gross_roi > Decimal("0"):
        return "Ruim", "bad"
    return "Sem ROI", "bad"


def _decimal(value: Any) -> Decimal | None:
    if value in (None, "", "--"):
        return None
    try:
        if isinstance(value, Decimal):
            return value
        txt = str(value).replace("R$", "").replace("%", "").strip().replace(" ", "")
        if "," in txt and "." in txt:
            txt = txt.replace(".", "").replace(",", ".")
        elif "," in txt:
            txt = txt.replace(",", ".")
        return Decimal(txt)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _int(value: Any, default: int = 1) -> int:
    dec = _decimal(value)
    if dec is None:
        return default
    try:
        parsed = int(dec)
    except Exception:
        return default
    return max(parsed, 1)


def _parse_date(value: Any, as_of: date) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    dte = _decimal(text)
    if dte is not None:
        return as_of + timedelta(days=max(int(dte), 0))
    return None


def _asset_from_record(record: dict[str, Any]) -> str:
    for key in ("ticker", "Ticker", "Ação", "Acao", "asset", "Asset"):
        value = record.get(key)
        if value:
            return str(value).strip().upper()
    option_code = str(record.get("Ativo") or record.get("option_code") or "").strip().upper()
    if option_code:
        return option_code[:5]
    return "ATIVO"


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


def _card_from_ranked(item: Any, indexed: dict[str, tuple[OptionOpportunity, Any]], *, source: str) -> RadarCard:
    opportunity, metrics = indexed[item.opportunity_id]
    roi_label, roi_class = _roi_concept(metrics.gross_roi)
    return RadarCard(
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
        roi_concept=roi_label,
        roi_concept_class=roi_class,
        source=source,
    )


def _evaluate_inputs(
    inputs: Iterable[tuple[OptionOpportunity, AssetQualityProfile, PutMetricAssumptions]],
    *,
    source: str,
) -> tuple[RadarCard, ...]:
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
    for opportunity, profile, assumptions in inputs:
        metrics = calculate_put_metrics(opportunity, assumptions)
        safety = evaluate_put_safety(opportunity, metrics, safety_config)
        quality = assess_asset_quality(profile, asset_policy)
        strategy = evaluate_put_strategy(opportunity, metrics, safety, quality)
        score = calculate_put_score(strategy, metrics, quality, score_config)
        opportunity_id = opportunity.option_code
        ranking_items.append((opportunity_id, strategy, score))
        indexed[opportunity_id] = (opportunity, metrics)

    ranked = rank_put_opportunities(ranking_items, RankingConfig(include_blocked=True))
    return tuple(_card_from_ranked(item, indexed, source=source) for item in ranked)


def build_demo_radar(as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Build UI-ready Radar cards from controlled demonstration opportunities."""

    as_of = as_of or date.today()
    inputs = tuple(
        (opportunity, profile, PutMetricAssumptions(as_of_date=as_of, contract_size=100, costs_total=Decimal("0")))
        for opportunity, profile in _demo_inputs(as_of)
    )
    return _evaluate_inputs(inputs, source="demo")


def build_radar_from_operations(operations: Iterable[dict[str, Any]], as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Build Radar cards from real operations already loaded by the Flask app.

    Invalid or incomplete rows are ignored instead of crashing the Radar screen.
    This keeps the UI safe while the real market provider layer is not ready yet.
    """

    as_of = as_of or date.today()
    inputs: list[tuple[OptionOpportunity, AssetQualityProfile, PutMetricAssumptions]] = []
    for record in operations:
        if str(record.get("Status", "")).lower() not in {"aberta", "open", ""}:
            continue
        if str(record.get("Tipo", "PUT")).upper() != "PUT":
            continue

        option_code = str(record.get("Ativo") or record.get("option_code") or "").strip().upper()
        asset = _asset_from_record(record)
        spot = _decimal(record.get("Cotacao_n") or record.get("cotacao_atual") or record.get("Cotacao_atual"))
        strike = _decimal(record.get("Strike_n") or record.get("Strike"))
        premium = _decimal(record.get("Premio_opcao_n") or record.get("Premio_opcao") or record.get("premium"))
        expiry = _parse_date(record.get("Vencimento") or record.get("Vencimento_fmt") or record.get("Dias"), as_of)
        if not option_code or spot is None or spot <= 0 or strike is None or strike <= 0 or premium is None or expiry is None:
            continue

        contratos = _int(record.get("Contratos_n") or record.get("Contratos"), default=1)
        costs = (_decimal(record.get("Custos_n") or record.get("Custos")) or Decimal("0")) + (
            _decimal(record.get("IRRF_n") or record.get("IRRF")) or Decimal("0")
        )
        opportunity = OptionOpportunity(
            asset=asset,
            option_code=option_code,
            option_type="PUT",
            expiry=expiry,
            spot_price=spot,
            strike=strike,
            premium=premium,
            data_confidence=Decimal("0.70"),
            source="operacao_real_cadastrada",
        )
        profile = AssetQualityProfile(
            asset=asset,
            assignment_eligible=True,
            long_term_suitable=True,
            quality_score=Decimal("0.65"),
            data_confidence=Decimal("0.55"),
            warnings=("Qualidade do ativo ainda precisa ser confirmada",),
            positive_notes=("Operação real cadastrada no sistema",),
            source="operacao_real_cadastrada",
        )
        assumptions = PutMetricAssumptions(
            as_of_date=as_of,
            contract_size=contratos * 100,
            costs_total=costs,
        )
        try:
            inputs.append((opportunity, profile, assumptions))
        except DecisionEngineError:
            continue

    if not inputs:
        return tuple()
    try:
        return _evaluate_inputs(inputs, source="real")
    except DecisionEngineError:
        return tuple()


def build_radar(operations: Iterable[dict[str, Any]] | None = None, as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Build Radar cards from real operations, falling back to demonstration data."""

    if operations is not None:
        real_cards = build_radar_from_operations(operations, as_of)
        if real_cards:
            return real_cards
    return build_demo_radar(as_of)
