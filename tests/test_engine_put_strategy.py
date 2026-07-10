import unittest
from datetime import date
from decimal import Decimal

from engine.asset import AssetQualityProfile, assess_asset_quality
from engine.core import OptionOpportunity
from engine.filters import FAILED, PASSED, SafetyCheck, SafetyEvaluation
from engine.metrics import PutMetricAssumptions, calculate_put_metrics
from engine.strategy import ELIGIBLE, INELIGIBLE, INSUFFICIENT_DATA, WATCHLIST, PutStrategyConfig, evaluate_put_strategy


class PutStrategyTests(unittest.TestCase):
    def _opportunity(self, **overrides):
        values = {
            "asset": "PETR4",
            "option_code": "PETRT280",
            "option_type": "PUT",
            "expiry": date(2026, 8, 21),
            "spot_price": Decimal("30"),
            "strike": Decimal("28"),
            "premium": Decimal("1.40"),
            "data_confidence": Decimal("0.80"),
        }
        values.update(overrides)
        return OptionOpportunity(**values)

    def _metrics(self, opportunity=None):
        return calculate_put_metrics(
            opportunity or self._opportunity(),
            PutMetricAssumptions(as_of_date=date(2026, 7, 10), contract_size=100),
        )

    def _asset(self, **overrides):
        values = {
            "asset": "PETR4",
            "assignment_eligible": True,
            "long_term_suitable": True,
            "quality_score": Decimal("0.90"),
            "data_confidence": Decimal("0.85"),
        }
        values.update(overrides)
        return assess_asset_quality(AssetQualityProfile(**values))

    def test_marks_put_as_initially_eligible_when_all_gates_pass(self):
        opportunity = self._opportunity()
        evaluation = evaluate_put_strategy(
            opportunity,
            self._metrics(opportunity),
            SafetyEvaluation(PASSED, tuple()),
            self._asset(),
            PutStrategyConfig(min_discount_to_market=Decimal("0.05"), min_capital_efficiency=Decimal("0.04")),
        )
        self.assertEqual(evaluation.status, ELIGIBLE)
        self.assertTrue(evaluation.eligible)
        self.assertEqual(evaluation.net_acquisition_price, Decimal("26.60"))

    def test_bad_asset_blocks_high_roi_put(self):
        opportunity = self._opportunity(premium=Decimal("5.00"))
        bad_asset = self._asset(assignment_eligible=False, quality_score=Decimal("0.95"))
        evaluation = evaluate_put_strategy(
            opportunity,
            self._metrics(opportunity),
            SafetyEvaluation(PASSED, tuple()),
            bad_asset,
        )
        self.assertEqual(evaluation.status, INELIGIBLE)
        self.assertIn("Asset not accepted for assignment", evaluation.blockers)

    def test_safety_failure_blocks_strategy(self):
        opportunity = self._opportunity()
        safety = SafetyEvaluation(
            FAILED,
            (SafetyCheck("spread_above_maximum", FAILED, "Spread too high"),),
        )
        evaluation = evaluate_put_strategy(opportunity, self._metrics(opportunity), safety, self._asset())
        self.assertEqual(evaluation.status, INELIGIBLE)
        self.assertIn("Safety filters failed", evaluation.blockers)

    def test_asset_insufficient_data_blocks_eligibility_without_calling_it_failed(self):
        opportunity = self._opportunity()
        asset = self._asset(quality_score=None)
        evaluation = evaluate_put_strategy(opportunity, self._metrics(opportunity), SafetyEvaluation(PASSED, tuple()), asset)
        self.assertEqual(evaluation.status, INSUFFICIENT_DATA)

    def test_low_discount_creates_watchlist_not_failure(self):
        opportunity = self._opportunity()
        evaluation = evaluate_put_strategy(
            opportunity,
            self._metrics(opportunity),
            SafetyEvaluation(PASSED, tuple()),
            self._asset(),
            PutStrategyConfig(min_discount_to_market=Decimal("0.20")),
        )
        self.assertEqual(evaluation.status, WATCHLIST)
        self.assertIn("Net acquisition discount below preferred minimum", evaluation.attention_points)

    def test_asset_mismatch_is_rejected(self):
        opportunity = self._opportunity()
        asset = self._asset(asset="VALE3")
        with self.assertRaises(Exception):
            evaluate_put_strategy(opportunity, self._metrics(opportunity), SafetyEvaluation(PASSED, tuple()), asset)
