"""Radar service for future market opportunity screens.

The public Radar is reserved for new market opportunities. Open positions are
kept outside this screen. Until a live provider is available, controlled demo
opportunities remain available for validation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

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
from services.concentration_service import MAX_ASSET_CONCENTRATION, PortfolioConcentration, concentration_reading


@dataclass(frozen=True, slots=True)
class RadarCard:
    position: int
    asset: str
    option_code: str
    option_premium: str
    strike: str
    expiry_date: str
    expiry_display: str
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
    source_label: str = "Fonte não identificada"
    data_mode: str = "Modalidade não informada"
    data_timestamp: str = "Não informado"
    data_age: str = "Idade desconhecida"
    freshness_status: str = "unknown"
    freshness_label: str = "Atualização não confirmada"
    confidence_pct: str = "—"
    confidence_label: str = "Não informada"
    confidence_class: str = "unknown"
    data_warning: str = "Confirme o preço e a data antes de decidir."
    concentration_pct: str = "—"
    concentration_label: str = "Não calculada"
    concentration_class: str = "unknown"
    concentration_message: str = "Carteira não informada."


def _money(value: Decimal) -> str:
    return f"R$ {value.quantize(Decimal('0.01'))}".replace(".", ",")


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%".replace(".", ",")


def _format_expiry(expiry: date, dte: int) -> tuple[str, str]:
    formatted = expiry.strftime("%d/%m/%Y")
    unit = "dia" if dte == 1 else "dias"
    return formatted, f"{formatted} - {dte} {unit}"


def _translate_explanation(text: str) -> str:
    """Translate known engine explanation fragments shown to the user."""
    replacements = {
        "Safety filters require attention": "Os filtros de segurança exigem atenção",
        "Asset quality requires attention": "A qualidade do ativo exige atenção",
        "Strategy checks require attention": "Os critérios da estratégia exigem atenção",
        "Insufficient data": "Dados insuficientes",
        "Operation is eligible": "A operação é elegível",
        "Operation is ineligible": "A operação não é elegível",
        "Asset concentration above maximum": "Concentração do ativo acima do limite",
    }
    translated = text
    for source, target in replacements.items():
        translated = translated.replace(source, target)
    return translated


def _roi_concept(gross_roi: Decimal) -> tuple[str, str]:
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
        text = str(value).replace("R$", "").replace("%", "").strip().replace(" ", "")
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _int(value: Any, default: int = 1) -> int:
    parsed = _decimal(value)
    if parsed is None:
        return default
    try:
        return max(int(parsed), 1)
    except Exception:
        return default


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
        if record.get(key):
            return str(record[key]).strip().upper()
    option_code = str(record.get("Ativo") or record.get("option_code") or "").strip().upper()
    return option_code[:5] if option_code else "ATIVO"


def _demo_inputs(as_of: date) -> tuple[tuple[OptionOpportunity, AssetQualityProfile], ...]:
    expiry = as_of + timedelta(days=35)
    return (
        (
            OptionOpportunity(
                asset="BBAS3", option_code="BBASQ270", option_type="PUT", expiry=expiry,
                spot_price=Decimal("28.50"), strike=Decimal("27.00"), premium=Decimal("1.10"),
                bid=Decimal("1.05"), ask=Decimal("1.15"), liquidity=Decimal("32000"),
                data_confidence=Decimal("0.92"), source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="BBAS3", assignment_eligible=True, long_term_suitable=True,
                quality_score=Decimal("0.88"), data_confidence=Decimal("0.90"),
                positive_notes=("Ativo aprovado para eventual exercício",), source="demo_controlado",
            ),
        ),
        (
            OptionOpportunity(
                asset="ITSA4", option_code="ITSAQ100", option_type="PUT", expiry=expiry,
                spot_price=Decimal("10.80"), strike=Decimal("10.00"), premium=Decimal("0.40"),
                bid=Decimal("0.36"), ask=Decimal("0.44"), liquidity=Decimal("18000"),
                data_confidence=Decimal("0.84"), source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="ITSA4", assignment_eligible=True, long_term_suitable=True,
                quality_score=Decimal("0.68"), data_confidence=Decimal("0.82"),
                warnings=("Qualidade aceitável, mas ainda abaixo do nível ideal",),
                positive_notes=("Preço líquido oferece desconto relevante",), source="demo_controlado",
            ),
        ),
        (
            OptionOpportunity(
                asset="ALTO3", option_code="ALTOQ150", option_type="PUT", expiry=expiry,
                spot_price=Decimal("16.00"), strike=Decimal("15.00"), premium=Decimal("1.20"),
                bid=Decimal("1.12"), ask=Decimal("1.28"), liquidity=Decimal("26000"),
                data_confidence=Decimal("0.76"), source="demo_controlado",
            ),
            AssetQualityProfile(
                asset="ALTO3", assignment_eligible=False, long_term_suitable=False,
                quality_score=Decimal("0.42"), data_confidence=Decimal("0.70"),
                blocking_events=("Ativo não aprovado para exercício",), source="demo_controlado",
            ),
        ),
    )


def _data_quality(opportunity: OptionOpportunity, as_of: date) -> dict[str, str]:
    raw_source = str(opportunity.source or "").lower()
    if "manual_intraday" in raw_source:
        source_label, mode, fresh_limit, warning_limit = "BTG / preço confirmado", "Intraday manual", 0, 1
    elif "b3" in raw_source or "cotahist" in raw_source:
        source_label, mode, fresh_limit, warning_limit = "B3 COTAHIST", "Fechamento EOD", 1, 3
    elif "csv" in raw_source:
        source_label, mode, fresh_limit, warning_limit = "CSV importado", "Arquivo manual", 1, 3
    elif "demo" in raw_source:
        source_label, mode, fresh_limit, warning_limit = "Demonstração controlada", "Dados de demonstração", 0, 0
    elif "operacao_real" in raw_source:
        source_label, mode, fresh_limit, warning_limit = "Cadastro interno", "Registro manual", 0, 1
    else:
        source_label, mode, fresh_limit, warning_limit = "Fonte não identificada", "Modalidade não informada", 0, 1

    timestamp = opportunity.timestamp
    if timestamp is None:
        freshness_status, freshness_label = "unknown", "Atualização não confirmada"
        data_timestamp, data_age = "Não informado", "Idade desconhecida"
        warning = "A data de referência não foi informada. Confirme o preço no BTG antes de decidir."
    else:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_days = max((as_of - timestamp.date()).days, 0)
        data_timestamp = timestamp.strftime("%d/%m/%Y às %H:%M") if timestamp.time() != datetime.min.time() else timestamp.strftime("%d/%m/%Y")
        data_age = "Hoje" if age_days == 0 else ("1 dia" if age_days == 1 else f"{age_days} dias")
        if age_days <= fresh_limit:
            freshness_status, freshness_label = "fresh", "Dados atuais"
            warning = "Dados dentro da janela esperada para esta modalidade."
        elif age_days <= warning_limit:
            freshness_status, freshness_label = "warning", "Atenção à atualização"
            warning = "Os dados podem estar defasados. Confirme o preço no BTG antes de decidir."
        else:
            freshness_status, freshness_label = "stale", "Dados defasados"
            warning = "Não tome decisão com estes valores sem atualizar o mercado e confirmar o preço no BTG."

    confidence = opportunity.data_confidence
    if confidence is None:
        confidence_pct, confidence_label, confidence_class = "—", "Não informada", "unknown"
    else:
        confidence_pct = f"{(confidence * Decimal('100')).quantize(Decimal('1'))}%"
        if confidence >= Decimal("0.85"):
            confidence_label, confidence_class = "Alta", "high"
        elif confidence >= Decimal("0.65"):
            confidence_label, confidence_class = "Média", "medium"
        else:
            confidence_label, confidence_class = "Baixa", "low"
            warning = "Confiança baixa nos dados. Atualize as fontes e confirme o preço no BTG antes de decidir."
    return {
        "source_label": source_label, "data_mode": mode, "data_timestamp": data_timestamp,
        "data_age": data_age, "freshness_status": freshness_status, "freshness_label": freshness_label,
        "confidence_pct": confidence_pct, "confidence_label": confidence_label,
        "confidence_class": confidence_class, "data_warning": warning,
    }


def _card_from_ranked(item: Any, indexed: dict[str, tuple[OptionOpportunity, Any]], *, source: str, as_of: date) -> RadarCard:
    opportunity, metrics = indexed[item.opportunity_id]
    roi_label, roi_class = _roi_concept(metrics.gross_roi)
    expiry_date, expiry_display = _format_expiry(opportunity.expiry, metrics.days_to_expiry)
    quality = _data_quality(opportunity, as_of)
    return RadarCard(
        position=item.position,
        asset=opportunity.asset,
        option_code=opportunity.option_code,
        option_premium=_money(opportunity.premium),
        strike=_money(opportunity.strike),
        expiry_date=expiry_date,
        expiry_display=expiry_display,
        status=item.summary.status,
        headline=_translate_explanation(item.summary.headline),
        reason=_translate_explanation(item.summary.reason),
        score=item.summary.score,
        gross_roi_pct=_pct(metrics.gross_roi),
        discount_pct=_pct(metrics.discount_to_market),
        net_price=_money(metrics.net_acquisition_price),
        capital=_money(metrics.nominal_committed_capital),
        dte=metrics.days_to_expiry,
        roi_concept=roi_label,
        roi_concept_class=roi_class,
        source=source,
        **quality,
    )


def _evaluate_inputs(
    inputs: Iterable[tuple[OptionOpportunity, AssetQualityProfile, PutMetricAssumptions]],
    *,
    source: str,
    as_of: date,
    portfolio: PortfolioConcentration | None = None,
) -> tuple[RadarCard, ...]:
    safety_config = SafetyFilterConfig(
        min_liquidity=Decimal("10000"), max_spread_pct=Decimal("0.25"),
        min_gross_roi=Decimal("0.04"), min_days_to_expiry=15, max_days_to_expiry=60,
    )
    asset_policy = AssetQualityPolicy(
        min_quality_score=Decimal("0.60"), attention_quality_score=Decimal("0.75"),
        min_data_confidence=Decimal("0.50"),
        max_concentration_pct=MAX_ASSET_CONCENTRATION if portfolio else None,
    )
    score_config = ExplainableScoreConfig(target_gross_roi=Decimal("0.04"))
    ranking_items: list[tuple[str, Any, Any]] = []
    indexed: dict[str, tuple[OptionOpportunity, Any]] = {}
    concentration_by_option: dict[str, Decimal | None] = {}
    for opportunity, profile, assumptions in inputs:
        metrics = calculate_put_metrics(opportunity, assumptions)
        projected = portfolio.projected_share(opportunity.asset, metrics.nominal_committed_capital) if portfolio else None
        concentration_by_option[opportunity.option_code] = projected
        if portfolio:
            profile = replace(profile, concentration_pct=projected)
        safety = evaluate_put_safety(opportunity, metrics, safety_config)
        quality = assess_asset_quality(profile, asset_policy)
        strategy = evaluate_put_strategy(opportunity, metrics, safety, quality)
        score = calculate_put_score(strategy, metrics, quality, score_config)
        ranking_items.append((opportunity.option_code, strategy, score))
        indexed[opportunity.option_code] = (opportunity, metrics)
    ranked = rank_put_opportunities(ranking_items, RankingConfig(include_blocked=True))
    cards = []
    for item in ranked:
        card = _card_from_ranked(item, indexed, source=source, as_of=as_of)
        projected = concentration_by_option.get(item.opportunity_id)
        status, label, message = concentration_reading(projected)
        cards.append(replace(
            card,
            concentration_pct=_pct(projected) if projected is not None else "—",
            concentration_label=label,
            concentration_class=status,
            concentration_message=message,
        ))
    return tuple(cards)


def build_demo_radar(as_of: date | None = None) -> tuple[RadarCard, ...]:
    as_of = as_of or date.today()
    inputs = tuple(
        (opportunity, profile, PutMetricAssumptions(as_of_date=as_of, contract_size=100, costs_total=Decimal("0")))
        for opportunity, profile in _demo_inputs(as_of)
    )
    return _evaluate_inputs(inputs, source="demo", as_of=as_of)


def build_radar_from_market(
    opportunities: Iterable[OptionOpportunity],
    quality_profiles: Mapping[str, AssetQualityProfile],
    as_of: date | None = None,
    portfolio: PortfolioConcentration | None = None,
) -> tuple[RadarCard, ...]:
    as_of = as_of or date.today()
    inputs: list[tuple[OptionOpportunity, AssetQualityProfile, PutMetricAssumptions]] = []
    for opportunity in opportunities:
        if opportunity.option_type != "PUT" or opportunity.expiry < as_of:
            continue
        profile = quality_profiles.get(opportunity.asset)
        if profile is None:
            profile = AssetQualityProfile(
                asset=opportunity.asset, assignment_eligible=False, long_term_suitable=False,
                data_confidence=Decimal("0.40"),
                blocking_events=("Ativo ainda não aprovado para eventual exercício",),
                source="cadastro_qualidade_pendente",
            )
        inputs.append((
            opportunity,
            profile,
            PutMetricAssumptions(as_of_date=as_of, contract_size=100, costs_total=Decimal("0")),
        ))
    if not inputs:
        return tuple()
    try:
        return _evaluate_inputs(inputs, source="b3_eod", as_of=as_of, portfolio=portfolio)
    except DecisionEngineError:
        return tuple()


def build_radar_from_operations(operations: Iterable[dict[str, Any]], as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Internal compatibility helper. Open operations are not used by the public Radar."""
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
            asset=asset, option_code=option_code, option_type="PUT", expiry=expiry,
            spot_price=spot, strike=strike, premium=premium, data_confidence=Decimal("0.70"),
            source="operacao_real_cadastrada",
        )
        profile = AssetQualityProfile(
            asset=asset, assignment_eligible=True, long_term_suitable=True,
            quality_score=Decimal("0.65"), data_confidence=Decimal("0.55"),
            warnings=("Qualidade do ativo ainda precisa ser confirmada",),
            positive_notes=("Registro interno avaliado sem substituir o scanner de mercado",),
            source="operacao_real_cadastrada",
        )
        inputs.append((
            opportunity,
            profile,
            PutMetricAssumptions(as_of_date=as_of, contract_size=contratos * 100, costs_total=costs),
        ))
    if not inputs:
        return tuple()
    try:
        return _evaluate_inputs(inputs, source="real", as_of=as_of)
    except DecisionEngineError:
        return tuple()


def build_radar(operations: Iterable[dict[str, Any]] | None = None, as_of: date | None = None) -> tuple[RadarCard, ...]:
    """Build the public Radar. Open operations are intentionally ignored."""
    return build_demo_radar(as_of)
