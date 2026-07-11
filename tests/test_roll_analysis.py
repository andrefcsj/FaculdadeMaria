from datetime import date
from decimal import Decimal
import unittest

from engine.roll import RollInput, analyze_put_roll


class RollAnalysisTests(unittest.TestCase):
    def base(self, **changes):
        values = dict(
            option_code="PETRT380",
            current_strike=Decimal("38"),
            original_premium=Decimal("1.20"),
            current_expiry=date(2026, 8, 21),
            buyback_price=Decimal("0.40"),
            new_option_code="PETRU370",
            new_strike=Decimal("37"),
            new_premium=Decimal("1.10"),
            new_expiry=date(2026, 9, 18),
            spot_price=Decimal("37.20"),
        )
        values.update(changes)
        return RollInput(**values)

    def test_recommends_roll_when_credit_risk_and_roi_improve(self):
        result = analyze_put_roll(self.base())
        self.assertEqual(result.recommendation, "roll")
        self.assertEqual(result.roll_credit_total, Decimal("70.00"))
        self.assertLess(result.new_net_price, result.current_net_price)
        self.assertGreaterEqual(result.new_cumulative_roi, Decimal("4.00"))

    def test_recommends_close_when_premium_is_captured_and_roll_does_not_improve(self):
        result = analyze_put_roll(self.base(
            buyback_price=Decimal("0.10"),
            new_strike=Decimal("39"),
            new_premium=Decimal("0.15"),
        ))
        self.assertEqual(result.recommendation, "close")

    def test_recommends_maintain_without_objective_improvement(self):
        result = analyze_put_roll(self.base(
            buyback_price=Decimal("0.80"),
            new_strike=Decimal("39"),
            new_premium=Decimal("0.85"),
        ))
        self.assertEqual(result.recommendation, "maintain")

    def test_rejects_expiry_that_is_not_later(self):
        with self.assertRaises(Exception):
            analyze_put_roll(self.base(new_expiry=date(2026, 8, 21)))


if __name__ == "__main__":
    unittest.main()
