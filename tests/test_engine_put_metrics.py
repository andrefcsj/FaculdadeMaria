import unittest
from datetime import date
from decimal import Decimal

from engine.core import OptionOpportunity
from engine.errors import EngineContractError
from engine.metrics import PutMetricAssumptions, calculate_put_metrics


class EnginePutMetricsTests(unittest.TestCase):
    def _opportunity(self, **overrides):
        values = {
            "asset": "PETR4",
            "option_code": "PETRT280",
            "option_type": "PUT",
            "expiry": date(2026, 8, 21),
            "spot_price": Decimal("30"),
            "strike": Decimal("28"),
            "premium": Decimal("1.40"),
        }
        values.update(overrides)
        return OptionOpportunity(**values)

    def test_calculates_auditable_put_metrics(self):
        metrics = calculate_put_metrics(
            self._opportunity(),
            PutMetricAssumptions(
                as_of_date=date(2026, 7, 10),
                contract_size=100,
                costs_total=Decimal("10"),
                committed_capital=Decimal("2000"),
                real_margin=Decimal("1500"),
            ),
        )
        self.assertEqual(metrics.days_to_expiry, 42)
        self.assertEqual(metrics.net_acquisition_price, Decimal("26.60"))
        self.assertEqual(metrics.gross_premium_income, Decimal("140.00"))
        self.assertEqual(metrics.nominal_committed_capital, Decimal("2800"))
        self.assertEqual(metrics.gross_roi, Decimal("0.05"))
        self.assertEqual(metrics.discount_to_market, Decimal("3.40") / Decimal("30"))
        self.assertEqual(metrics.strike_distance_pct, Decimal("2") / Decimal("30"))
        self.assertEqual(metrics.annualized_roi, Decimal("0.05") * Decimal("365") / Decimal("42"))
        self.assertEqual(metrics.return_per_day, Decimal("0.05") / Decimal("42"))
        self.assertEqual(metrics.net_premium_income, Decimal("130.00"))
        self.assertEqual(metrics.net_roi, Decimal("130") / Decimal("2800"))
        self.assertEqual(metrics.capital_efficiency, Decimal("0.07"))
        self.assertEqual(metrics.return_on_margin, Decimal("140") / Decimal("1500"))
        self.assertEqual(metrics.capital_basis, "explicit_committed_capital")
        self.assertEqual(metrics.annualization_method, "simple")

    def test_does_not_invent_costs_margin_or_committed_capital(self):
        metrics = calculate_put_metrics(
            self._opportunity(),
            PutMetricAssumptions(as_of_date=date(2026, 7, 10), contract_size=100),
        )
        self.assertIsNone(metrics.net_roi)
        self.assertIsNone(metrics.net_premium_income)
        self.assertIsNone(metrics.return_on_margin)
        self.assertEqual(metrics.capital_basis, "nominal_cash_secured")
        self.assertEqual(metrics.capital_efficiency, metrics.gross_roi)

    def test_zero_dte_avoids_misleading_annualization(self):
        metrics = calculate_put_metrics(
            self._opportunity(expiry=date(2026, 7, 10)),
            PutMetricAssumptions(as_of_date=date(2026, 7, 10)),
        )
        self.assertEqual(metrics.days_to_expiry, 0)
        self.assertIsNone(metrics.annualized_roi)
        self.assertIsNone(metrics.net_annualized_roi)
        self.assertIsNone(metrics.return_per_day)

    def test_rejects_expired_opportunity(self):
        with self.assertRaises(EngineContractError):
            calculate_put_metrics(
                self._opportunity(expiry=date(2026, 7, 9)),
                PutMetricAssumptions(as_of_date=date(2026, 7, 10)),
            )

    def test_rejects_missing_required_metric_fields(self):
        with self.assertRaises(EngineContractError) as ctx:
            calculate_put_metrics(
                self._opportunity(premium=None),
                PutMetricAssumptions(as_of_date=date(2026, 7, 10)),
            )
        self.assertEqual(ctx.exception.details["missing_fields"], ["premium"])

    def test_rejects_call_for_put_metrics(self):
        with self.assertRaises(EngineContractError):
            calculate_put_metrics(
                self._opportunity(option_type="CALL"),
                PutMetricAssumptions(as_of_date=date(2026, 7, 10)),
            )

    def test_rejects_invalid_assumptions(self):
        with self.assertRaises(EngineContractError):
            PutMetricAssumptions(as_of_date=date(2026, 7, 10), contract_size=0)
        with self.assertRaises(EngineContractError):
            PutMetricAssumptions(as_of_date=date(2026, 7, 10), costs_total=Decimal("-1"))

    def test_same_input_produces_same_output(self):
        opportunity = self._opportunity()
        assumptions = PutMetricAssumptions(as_of_date=date(2026, 7, 10), contract_size=100)
        first = calculate_put_metrics(opportunity, assumptions)
        second = calculate_put_metrics(opportunity, assumptions)
        self.assertEqual(first, second)
