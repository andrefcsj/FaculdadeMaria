from decimal import Decimal
from unittest import TestCase

from engine.errors import EngineContractError
from engine.explain import summarize_put_operation
from engine.ranking import RankingConfig, rank_put_opportunities
from engine.score.explainable import (
    SCORE_BLOCKED,
    SCORE_READY,
    SCORE_WATCHLIST,
    ScoreEvaluation,
)
from engine.strategy.put import ELIGIBLE, INELIGIBLE, WATCHLIST, PutStrategyEvaluation


def _strategy(
    *,
    status=ELIGIBLE,
    positives=("Ativo adequado para exercício",),
    attention=(),
    blockers=(),
    gross_roi=Decimal("0.05"),
    discount=Decimal("0.08"),
    efficiency=Decimal("0.05"),
    confidence=Decimal("0.90"),
):
    return PutStrategyEvaluation(
        status=status,
        checks=tuple(),
        positive_factors=positives,
        attention_points=attention,
        blockers=blockers,
        conclusion="test conclusion",
        net_acquisition_price=Decimal("26.60"),
        gross_roi=gross_roi,
        discount_to_market=discount,
        capital_efficiency=efficiency,
        safety_status="passed",
        asset_quality_status="passed",
        data_confidence=confidence,
    )


def _score(*, value=Decimal("88"), status=SCORE_READY, confidence=Decimal("0.90")):
    return ScoreEvaluation(
        score=value,
        status=status,
        components=tuple(),
        penalties=tuple(),
        data_confidence=confidence,
        target_gross_roi=Decimal("0.04"),
        explanation="test score",
    )


class RankingExplanationTests(TestCase):
    def test_eligible_summary_is_short_and_practical(self):
        summary = summarize_put_operation(_strategy(), _score())

        self.assertEqual(summary.status, "eligible")
        self.assertEqual(summary.headline, "Operação elegível")
        self.assertIn("Score 88/100", summary.reason)
        self.assertIn("ROI 5.00%", summary.reason)
        self.assertLessEqual(len(summary.reason), 220)

    def test_discarded_summary_uses_blocker(self):
        summary = summarize_put_operation(
            _strategy(status=INELIGIBLE, positives=tuple(), blockers=("Ativo não aceito para exercício",)),
            _score(value=Decimal("0"), status=SCORE_BLOCKED),
        )

        self.assertEqual(summary.status, "discarded")
        self.assertEqual(summary.headline, "Operação descartada")
        self.assertEqual(summary.main_blocker, "Ativo não aceito para exercício")
        self.assertIn("Ativo não aceito", summary.reason)

    def test_watchlist_summary_uses_attention_point(self):
        summary = summarize_put_operation(
            _strategy(status=WATCHLIST, attention=("Spread exige atenção",)),
            _score(value=Decimal("72"), status=SCORE_WATCHLIST),
        )

        self.assertEqual(summary.status, "watchlist")
        self.assertIn("Spread exige atenção", summary.reason)

    def test_ranking_prioritizes_eligible_higher_score(self):
        ranked = rank_put_opportunities(
            (
                ("PUT_B", _strategy(gross_roi=Decimal("0.04")), _score(value=Decimal("70"))),
                ("PUT_A", _strategy(gross_roi=Decimal("0.06")), _score(value=Decimal("91"))),
            )
        )

        self.assertEqual(ranked[0].opportunity_id, "PUT_A")
        self.assertEqual(ranked[0].position, 1)
        self.assertEqual(ranked[0].summary.status, "eligible")

    def test_ranking_keeps_blocked_explainable_by_default(self):
        ranked = rank_put_opportunities(
            (
                ("RUIM", _strategy(status=INELIGIBLE, positives=tuple(), blockers=("Ativo ruim",)), _score(value=Decimal("0"), status=SCORE_BLOCKED)),
                ("BOA", _strategy(), _score(value=Decimal("80"))),
            )
        )

        self.assertEqual(tuple(item.opportunity_id for item in ranked), ("BOA", "RUIM"))
        self.assertEqual(ranked[1].summary.status, "discarded")
        self.assertEqual(ranked[1].rank_score, Decimal("0"))

    def test_ranking_can_hide_blocked(self):
        ranked = rank_put_opportunities(
            (
                ("RUIM", _strategy(status=INELIGIBLE, positives=tuple(), blockers=("Ativo ruim",)), _score(value=Decimal("0"), status=SCORE_BLOCKED)),
                ("BOA", _strategy(), _score(value=Decimal("80"))),
            ),
            RankingConfig(include_blocked=False),
        )

        self.assertEqual(tuple(item.opportunity_id for item in ranked), ("BOA",))

    def test_invalid_summary_limit_is_rejected(self):
        with self.assertRaises(EngineContractError):
            summarize_put_operation(_strategy(), _score(), max_reason_chars=20)
