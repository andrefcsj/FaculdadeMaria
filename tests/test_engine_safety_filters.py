import unittest
from datetime import date
from decimal import Decimal

from engine.core import OptionOpportunity
from engine.errors import EngineContractError
from engine.filters import ATTENTION, FAILED, PASSED, SafetyFilterConfig, evaluate_put_safety
from engine.metrics import PutMetrics


class EngineSafetyFilterTests(unittest.TestCase):
    def _opportunity(self, **overrides):
        values = {
            "asset": "PETR4",
            "option_code": "PETRT280",
            "option_type": "PUT",
            "expiry": date(2026, 8, 21),
            "spot_price": Decimal("30"),
            "strike": Decimal("28"),
            "premium": Decimal("1.40"),
            "bid": Decimal("1.35"),
            "ask": Decimal("1.45"),
            "liquidity": Decimal("0.80"),
        }
        values.update(overrides)
        return OptionOpportunity(**values)

    def _metrics(self, **overrides):
        values = {
            "net_acquisition_price": Decimal("26.60"),
            "discount_to_market": Decimal("0.1133333333333333333333333333"),
            "gross_roi": Decimal("0.05"),
            "net_roi": None,
            "annualized_roi": Decimal("0.43"),
            "net_annualized_roi": None,
            "strike_distance_pct": Decimal("0.0666666666666666666666666667"),
            "days_to_expiry": 42,
            "return_per_day": Decimal("0.00119"),
            "gross_premium_income": Decimal("140"),
            "net_premium_income": None,
            "nominal_committed_capital": Decimal("2800"),
            "capital_efficiency": Decimal("0.05"),
            "return_on_margin": None,
            "capital_basis": "nominal_cash_secured",
            "annualization_method": "simple",
            "annualization_days": 365,
            "contract_size": 100,
        }
        values.update(overrides)
        return PutMetrics(**values)

    def test_passes_configured_safety_checks(self):
        result = evaluate_put_safety(
            self._opportunity(),
            self._metrics(),
            SafetyFilterConfig(
                min_liquidity=Decimal("0.5"),
                max_spread_pct=Decimal("0.10"),
                min_gross_roi=Decimal("0.03"),
                min_days_to_expiry=20,
                max_days_to_expiry=60,
            ),
        )
        self.assertEqual(result.status, PASSED)
        self.assertTrue(result.passed)
        self.assertEqual(result.failed_checks, ())

    def test_fails_missing_required_data(self):
        result = evaluate_put_safety(self._opportunity(premium=None))
        self.assertEqual(result.status, FAILED)
        self.assertEqual(result.failed_checks[0].code, "missing_required_data")

    def test_flags_missing_liquidity_as_attention(self):
        result = evaluate_put_safety(
            self._opportunity(liquidity=None),
            config=SafetyFilterConfig(min_liquidity=Decimal("0.5")),
        )
        self.assertEqual(result.status, ATTENTION)
        self.assertEqual(result.attention_checks[0].code, "liquidity_missing")

    def test_fails_low_liquidity_and_wide_spread(self):
        result = evaluate_put_safety(
            self._opportunity(liquidity=Decimal("0.1"), bid=Decimal("1.00"), ask=Decimal("1.50")),
            config=SafetyFilterConfig(min_liquidity=Decimal("0.5"), max_spread_pct=Decimal("0.20")),
        )
        self.assertEqual(result.status, FAILED)
        self.assertEqual(
            {check.code for check in result.failed_checks},
            {"liquidity_below_minimum", "spread_above_maximum"},
        )

    def test_fails_roi_and_dte_thresholds(self):
        result = evaluate_put_safety(
            self._opportunity(),
            self._metrics(gross_roi=Decimal("0.01"), days_to_expiry=5),
            SafetyFilterConfig(min_gross_roi=Decimal("0.03"), min_days_to_expiry=10, max_days_to_expiry=60),
        )
        self.assertEqual(result.status, FAILED)
        self.assertIn("gross_roi_below_minimum", {check.code for check in result.failed_checks})
        self.assertIn("dte_below_minimum", {check.code for check in result.failed_checks})

    def test_fails_itm_put_when_not_allowed(self):
        result = evaluate_put_safety(self._opportunity(strike=Decimal("31")))
        self.assertEqual(result.status, FAILED)
        self.assertEqual(result.failed_checks[0].code, "put_strike_above_spot")

    def test_metrics_missing_attention(self):
        result = evaluate_put_safety(
            self._opportunity(),
            config=SafetyFilterConfig(min_gross_roi=Decimal("0.03")),
        )
        self.assertEqual(result.status, ATTENTION)
        self.assertEqual(result.attention_checks[0].code, "metrics_missing")

    def test_rejects_invalid_config(self):
        with self.assertRaises(EngineContractError):
            evaluate_put_safety(
                self._opportunity(),
                config=SafetyFilterConfig(min_days_to_expiry=60, max_days_to_expiry=30),
            )
