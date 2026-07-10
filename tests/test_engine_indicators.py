import unittest
from decimal import Decimal

from engine.errors import EngineContractError
from engine.indicators import (
    average_true_range,
    bollinger_bands,
    historical_volatility,
    moving_average_21,
    moving_average_200,
    relative_strength_index,
    simple_moving_average,
    strike_distance_in_atr,
    true_range,
)


class EngineIndicatorTests(unittest.TestCase):
    def test_simple_moving_average_and_insufficient_history(self):
        self.assertIsNone(simple_moving_average([1, 2], 3))
        self.assertEqual(simple_moving_average([1, 2, 3, 4], 3), Decimal("3"))

    def test_moving_average_helpers(self):
        self.assertEqual(moving_average_21(range(1, 22)), Decimal("11"))
        self.assertEqual(moving_average_200(range(1, 201)), Decimal("100.5"))

    def test_relative_strength_index(self):
        values = [Decimal("10"), Decimal("11"), Decimal("12"), Decimal("11"), Decimal("13")]
        result = relative_strength_index(values, period=4)
        self.assertEqual(result, Decimal("80"))
        self.assertEqual(relative_strength_index([10, 10, 10, 10, 10], period=4), Decimal("50"))
        self.assertIsNone(relative_strength_index([1, 2, 3], period=4))

    def test_bollinger_bands(self):
        bands = bollinger_bands([1, 2, 3, 4, 5], period=5, deviations=Decimal("2"))
        self.assertEqual(bands.middle, Decimal("3"))
        self.assertEqual(bands.standard_deviation, Decimal("2").sqrt())
        self.assertEqual(bands.upper, Decimal("3") + Decimal("2") * Decimal("2").sqrt())
        self.assertEqual(bands.lower, Decimal("3") - Decimal("2") * Decimal("2").sqrt())

    def test_true_range_and_atr(self):
        self.assertEqual(true_range("12", "10", "11"), Decimal("2"))
        highs = [10, 12, 13, 14]
        lows = [9, 10, 11, 13]
        closes = [9, 11, 12, 13]
        self.assertEqual(average_true_range(highs, lows, closes, period=3), Decimal("7") / Decimal("3"))

    def test_historical_volatility(self):
        closes = [100, 101, 102, 103, 104]
        result = historical_volatility(closes, period=4, annualization_days=252)
        self.assertIsNotNone(result)
        self.assertGreater(result, Decimal("0"))
        self.assertEqual(historical_volatility([100, 101], period=4), None)

    def test_strike_distance_in_atr(self):
        self.assertEqual(strike_distance_in_atr("30", "28", "1"), Decimal("2"))
        self.assertIsNone(strike_distance_in_atr("30", "28", None))
        self.assertIsNone(strike_distance_in_atr("30", "28", "0"))

    def test_rejects_invalid_indicator_inputs(self):
        with self.assertRaises(EngineContractError):
            simple_moving_average([1, True], 2)
        with self.assertRaises(EngineContractError):
            simple_moving_average([1, 2], 0)
        with self.assertRaises(EngineContractError):
            average_true_range([10], [11], [10], period=1)
