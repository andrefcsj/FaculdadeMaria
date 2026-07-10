"""Concise explanations for PUT opportunities.

This module creates short, user-facing summaries for future Radar screens. It
keeps explanations compact and does not create recommendations outside the
strategy and score outputs already produced by the engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..errors import EngineContractError
from ..score.explainable import (
    SCORE_BLOCKED,
    SCORE_INSUFFICIENT_DATA,
    SCORE_READY,
    SCORE_WATCHLIST,
    ScoreEvaluation,
)
from ..strategy.put import ELIGIBLE, INELIGIBLE, INSUFFICIENT_DATA, WATCHLIST, PutStrategyEvaluation


@dataclass(frozen=True, slots=True)
class OperationSummary:
    """Short explanation prepared for UI display."""

    status: str
    headline: str
    reason: str
    main_positive: str | None = None
    main_attention: str | None = None
    main_blocker: str | None = None
    score: int | None = None


def _pct(value: Decimal | None) -> str | None:
    if value is None:
        return None
    pct = value * Decimal("100")
    return f"{pct.quantize(Decimal('0.01'))}%"


def _first(values: tuple[str, ...]) -> str | None:
    return values[0] if values else None


def _score_value(score: ScoreEvaluation) -> int | None:
    if score.status in {SCORE_BLOCKED, SCORE_INSUFFICIENT_DATA}:
        return None
    return score.score_int


def summarize_put_operation(
    strategy: PutStrategyEvaluation,
    score: ScoreEvaluation,
    *,
    max_reason_chars: int = 220,
) -> OperationSummary:
    """Create a short explanation for a PUT opportunity.

    The summary is intentionally brief: one headline and one practical reason.
    """

    if not isinstance(strategy, PutStrategyEvaluation):
        raise EngineContractError("strategy must be PutStrategyEvaluation")
    if not isinstance(score, ScoreEvaluation):
        raise EngineContractError("score must be ScoreEvaluation")
    if isinstance(max_reason_chars, bool) or not isinstance(max_reason_chars, int) or max_reason_chars < 80:
        raise EngineContractError("max_reason_chars must be an integer greater than or equal to 80")

    main_positive = _first(strategy.positive_factors)
    main_attention = _first(strategy.attention_points)
    main_blocker = _first(strategy.blockers)
    score_int = _score_value(score)
    roi = _pct(strategy.gross_roi)
    discount = _pct(strategy.discount_to_market)

    if strategy.status == INELIGIBLE or score.status == SCORE_BLOCKED:
        headline = "Operação descartada"
        reason = main_blocker or "A PUT falhou nos filtros obrigatórios da estratégia."
        summary_status = "discarded"
    elif strategy.status == INSUFFICIENT_DATA or score.status == SCORE_INSUFFICIENT_DATA:
        headline = "Dados insuficientes"
        reason = main_attention or "Faltam dados para avaliar a operação com segurança."
        summary_status = "insufficient_data"
    elif strategy.status == WATCHLIST or score.status == SCORE_WATCHLIST:
        headline = "Operação em observação"
        score_part = f"Score {score_int}/100" if score_int is not None else "Score em observação"
        reason = f"{score_part}. {main_attention or 'Há pontos que exigem atenção antes da execução.'}"
        summary_status = "watchlist"
    elif strategy.status == ELIGIBLE or score.status == SCORE_READY:
        headline = "Operação elegível"
        score_part = f"Score {score_int}/100" if score_int is not None else "Score calculado"
        positive = main_positive or "A operação passou nos critérios principais."
        metrics = []
        if roi is not None:
            metrics.append(f"ROI {roi}")
        if discount is not None:
            metrics.append(f"desconto {discount}")
        metric_text = f" ({', '.join(metrics)})" if metrics else ""
        reason = f"{score_part}{metric_text}. {positive}"
        summary_status = "eligible"
    else:
        headline = "Operação sem conclusão"
        reason = "O motor não conseguiu resumir o status da operação."
        summary_status = "unknown"

    if len(reason) > max_reason_chars:
        reason = reason[: max_reason_chars - 1].rstrip() + "…"

    return OperationSummary(
        status=summary_status,
        headline=headline,
        reason=reason,
        main_positive=main_positive,
        main_attention=main_attention,
        main_blocker=main_blocker,
        score=score_int,
    )
