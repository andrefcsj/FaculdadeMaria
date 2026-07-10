import unittest
from decimal import Decimal

from engine.asset import (
    ATTENTION,
    FAILED,
    INSUFFICIENT_DATA,
    PASSED,
    AssetQualityPolicy,
    AssetQualityProfile,
    assess_asset_quality,
)
from engine.errors import EngineContractError


class AssetQualityTests(unittest.TestCase):
    def test_passes_quality_for_assignment_ready_asset(self):
        assessment = assess_asset_quality(
            AssetQualityProfile(
                asset="PETR4",
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=Decimal("0.86"),
                data_confidence=Decimal("0.90"),
                positive_notes=("blue chip",),
            )
        )
        self.assertEqual(assessment.status, PASSED)
        self.assertIn("Asset accepted for assignment", assessment.positive_factors)

    def test_fails_when_asset_is_not_assignment_eligible_even_with_score(self):
        assessment = assess_asset_quality(
            AssetQualityProfile(
                asset="XYZ",
                assignment_eligible=False,
                long_term_suitable=True,
                quality_score=Decimal("0.95"),
                data_confidence=Decimal("0.95"),
            )
        )
        self.assertEqual(assessment.status, FAILED)
        self.assertIn("Asset not accepted for assignment", assessment.blockers)

    def test_insufficient_when_quality_score_missing(self):
        assessment = assess_asset_quality(
            AssetQualityProfile(
                asset="VALE3",
                assignment_eligible=True,
                long_term_suitable=True,
                data_confidence=Decimal("0.90"),
            )
        )
        self.assertEqual(assessment.status, INSUFFICIENT_DATA)

    def test_attention_for_acceptable_but_not_strong_quality(self):
        assessment = assess_asset_quality(
            AssetQualityProfile(
                asset="ABEV3",
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=Decimal("0.65"),
                data_confidence=Decimal("0.90"),
            )
        )
        self.assertEqual(assessment.status, ATTENTION)
        self.assertIn("Asset quality is acceptable but not strong", assessment.warnings)

    def test_fails_concentration_above_limit(self):
        assessment = assess_asset_quality(
            AssetQualityProfile(
                asset="ITUB4",
                assignment_eligible=True,
                long_term_suitable=True,
                quality_score=Decimal("0.90"),
                data_confidence=Decimal("0.90"),
                concentration_pct=Decimal("0.35"),
            ),
            AssetQualityPolicy(max_concentration_pct=Decimal("0.20")),
        )
        self.assertEqual(assessment.status, FAILED)
        self.assertIn("Asset concentration above maximum", assessment.blockers)

    def test_rejects_invalid_ratio(self):
        with self.assertRaises(EngineContractError):
            AssetQualityProfile(asset="PETR4", quality_score=Decimal("1.20"))
