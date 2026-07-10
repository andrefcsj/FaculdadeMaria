"""Ranking helpers for PUT opportunities.

Ranking is deterministic and explainable. It does not fetch data, access Flask,
or create a final trading order. It only sorts already evaluated opportunities.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from ..errors import EngineContractError
from ..explain.summary import OperationSummary, summarize_put_operation
from ..score.explainable import (
    SCORE_BLOCKED,
    SCORE_INSUFFICIENT_DATA,
    SCORE_READY,
    SCORE_WATCHLIST,
    ScoreEvaluation,
)
from ..strategy.put import ELIGIBLE, INELIGIBLE, INSUFFICIENT_DATA, WATCHLIST, PutStrategyEvaluation


@dataclass(frozen=True, slots=True)
class RankingConfig:
    """Tie-break rules for already evaluated opportunities."""

    include_blocked: bool = True
    prefer_higher_confidence: bool = True


@dataclass(frozen=True, slots=True)
class RankedOpportunity:
    """Ranked opportunity ready for a future Radar service/UI."""

    position: int
    opportunity_id: str
    status: str
    rank_score: Decimal
    score: ScoreEvaluation
    strategy: PutStrategyEvaluation
    summary: OperationSummary
    sort_key: tuple


def _validate_item(item: tuple[str, PutStrategyEvaluation, ScoreEvaluation]) -> tuple[str, PutStrategyEvaluation, ScoreEvaluation]:
    if not isinstance(item, tuple) or len(item) != 3:
        raise EngineContractError("Each ranking item must be a tuple: (opportunity_id, strategy, score)")
    opportunity_id, strategy, score = item
    if not isinstance(opportunity_id, str) or not opportunity_id.strip():
        raise EngineContractError("opportunity_id must be a non-empty string")
    if not isinstance(strategy, PutStrategyEvaluation):
        raise EngineContractError("ranking strategy must be PutStrategyEvaluation")
    if not isinstance(score, ScoreEvaluation):
        raise EngineContractError("ranking score must be ScoreEvaluation")
    return opportunity_id.strip(), strategy, score


def _status_priority(strategy_status: str, score_status: str) -> int:
    if strategy_status == ELIGIBLE and score_status == SCORE_READY:
        return 4
    if strategy_status == WATCHLIST or score_status == SCORE_WATCHLIST:
        return 3
    if strategy_status == INSUFFICIENT_DATA or score_status == SCORE_INSUFFICIENT_DATA:
        return 2
    if strategy_status == INELIGIBLE or score_status == SCORE_BLOCKED:
        return 1
    return 0


def _confidence(score: ScoreEvaluation) -> Decimal:
    return score.data_confidence if score.data_confidence is not None else Decimal("0")


def _rank_score(strategy: PutStrategyEvaluation, score: ScoreEvaluation) -> Decimal:
    if strategy.status == INELIGIBLE or score.status == SCORE_BLOCKED:
        return Decimal("0")
    if strategy.status == INSUFFICIENT_DATA or score.status == SCORE_INSUFFICIENT_DATA:
        return Decimal("0")
    return score.score


def _sort_key(strategy: PutStrategyEvaluation, score: ScoreEvaluation, *, prefer_higher_confidence: bool) -> tuple:
    confidence = _confidence(score) if prefer_higher_confidence else Decimal("0")
    return (
        _status_priority(strategy.status, score.status),
        _rank_score(strategy, score),
        strategy.discount_to_market,
        strategy.gross_roi,
        strategy.capital_efficiency,
        confidence,
    )


def rank_put_opportunities(
    items: Iterable[tuple[str, PutStrategyEvaluation, ScoreEvaluation]],
    config: RankingConfig | None = None,
) -> tuple[RankedOpportunity, ...]:
    """Rank evaluated PUT opportunities.

    Input items must already contain strategy and score evaluations. The function
    keeps blocked opportunities explainable, unless explicitly filtered out.
    """

    config = config or RankingConfig()
    if not isinstance(config, RankingConfig):
        raise EngineContractError("config must be RankingConfig")

    ranked: list[RankedOpportunity] = []
    for raw_item in items:
        opportunity_id, strategy, score = _validate_item(raw_item)
        if not config.include_blocked and (strategy.status == INELIGIBLE or score.status == SCORE_BLOCKED):
            continue
        summary = summarize_put_operation(strategy, score)
        sort_key = _sort_key(strategy, score, prefer_higher_confidence=config.prefer_higher_confidence)
        ranked.append(
            RankedOpportunity(
                position=0,
                opportunity_id=opportunity_id,
                status=summary.status,
                rank_score=_rank_score(strategy, score),
                score=score,
                strategy=strategy,
                summary=summary,
                sort_key=sort_key,
            )
        )

    ordered = sorted(ranked, key=lambda item: item.sort_key, reverse=True)
    return tuple(
        RankedOpportunity(
            position=index,
            opportunity_id=item.opportunity_id,
            status=item.status,
            rank_score=item.rank_score,
            score=item.score,
            strategy=item.strategy,
            summary=item.summary,
            sort_key=item.sort_key,
        )
        for index, item in enumerate(ordered, start=1)
    )
