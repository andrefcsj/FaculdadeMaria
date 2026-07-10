import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from engine import (
    DEFAULT_TARGET_GROSS_ROI,
    AssetQualityPolicy,
    AssetQualityProfile,
    ExplainableScoreConfig,
    OptionOpportunity,
    PutMetricAssumptions,
    PutStrategyConfig,
    SafetyFilterConfig,
    assess_asset_quality,
    calculate_put_metrics,
    calculate_put_score,
    evaluate_put_safety,
    evaluate_put_strategy,
)


class ExplainablePutScoreTest(unittest.TestCase):
    def _opportunity(self, *, premium=Decimal("1.12")):
        return OptionOpportunity(
            asset="BBDC4",
            option_code="BBDCP280",
            option_type="PUT",
            expiry=date(2026, 8, 21),
            spot_price=Decimal("30"),
            strike=Decimal("28"),
            premium=premium,
            bid=premium,
            ask=premium,
            liquidity=Decimal("1000"),
            timestamp=datetime(2026, 7, 10, 12, tzinfo=timezone.utc),
            source="unit-test",
            data_confidence=Decimal("0.90"),
        )

    def _evaluation(self, *, premium=Decimal("1.12"), asset_quality_score=Decimal("0.80"), assignment=True):
        opportunity = self._opportunity(premium=premium)
        metrics = calculate_put_metrics(
            opportunity,
            PutMetricAssumptions(as_of_date=date(2026, 7, 10)),
        )
        safety = evaluate_put_safety(
            opportunity,
            metrics,
            SafetyFilterConfig(
                min_liquidity=Decimal("100"),
                max_spread_pct=Decimal("0.10"),
                min_gross_roi=Decimal("0.04"),
                min_days_to_expiry=20,
                max_days_to_expiry=90,
            ),
        )
        asset_quality = assess_asset_quality(
            AssetQualityProfile(
                asset="BBDC4",
                assignment_eligible=assignment,
                long_term_suitable=True,
                quality_score=asset_quality_score,
                data_confidence=Decimal("0.85"),
                positive_notes=("Eligible asset for systematic PUT selling",),
            ),
            AssetQualityPolicy(),
        )
        strategy = evaluate_put_strategy(
            opportunity,
            metrics,
            safety,
            asset_quality,
            PutStrategyConfig(
                min_discount_to_market=Decimal("0.05"),
                min_capital_efficiency=Decimal("0.04"),
            ),
        )
        return metrics, asset_quality, strategy

    def test_default_roi_target_is_four_percent(self):
        self.assertEqual(DEFAULT_TARGET_GROSS_ROI, Decimal("0.04"))
        self.assertEqual(ExplainableScoreConfig().target_gross_roi, Decimal("0.04"))

    def test_score_ready_for_eligible_put(self):
        metrics, asset_quality, strategy = self._evaluation()
        score = calculate_put_score(strategy, metrics, asset_quality)

        self.assertEqual(score.status, "score_ready")
        self.assertGreater(score.score, Decimal("90"))
        self.assertEqual(score.target_gross_roi, Decimal("0.04"))
        self.assertEqual(score.data_confidence, Decimal("0.85"))
        self.assertEqual(len(score.components), 5)

    def test_roi_component_uses_four_percent_target(self):
        metrics, asset_quality, strategy = self._evaluation(premium=Decimal("0.56"))
        score = calculate_put_score(strategy, metrics, asset_quality)
        roi_component = next(component for component in score.components if component.code == "gross_roi_vs_target")

        self.assertEqual(metrics.gross_roi, Decimal("0.02"))
        self.assertEqual(roi_component.factor, Decimal("0.5"))

    def test_ineligible_strategy_blocks_score_even_with_high_roi(self):
        metrics, asset_quality, strategy = self._evaluation(premium=Decimal("2.80"), assignment=False)
        score = calculate_put_score(strategy, metrics, asset_quality)

        self.assertEqual(strategy.status, "ineligible")
        self.assertEqual(score.status, "score_blocked")
        self.assertEqual(score.score, Decimal("0"))
        self.assertTrue(score.penalties)

    def test_score_watchlist_when_strategy_requires_attention(self):
        metrics, asset_quality, strategy = self._evaluation(asset_quality_score=Decimal("0.70"))
        score = calculate_put_score(strategy, metrics, asset_quality)

        self.assertEqual(strategy.status, "watchlist")
        self.assertEqual(score.status, "score_watchlist")
        self.assertGreater(score.score, Decimal("0"))

    def test_invalid_config_rejects_zero_roi_target(self):
        with self.assertRaises(Exception):
            ExplainableScoreConfig(target_gross_roi=Decimal("0"))


if __name__ == "__main__":
    unittest.main()
