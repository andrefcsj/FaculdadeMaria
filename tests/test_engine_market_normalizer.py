import unittest
from decimal import Decimal

from engine.errors import EngineContractError
from engine.market import normalize_market_snapshot


class EngineMarketNormalizerTests(unittest.TestCase):
    def test_normalizes_decimal_comma_and_preserves_traceability(self):
        snapshot = normalize_market_snapshot(
            {
                "asset": "PETR4",
                "option_code": "PETRT280",
                "option_type": "put",
                "expiry": "21/08/2026",
                "spot_price": "30,00",
                "strike": "28.00",
                "premium": "1,40",
                "bid": "1,35",
                "ask": "1,45",
                "volume": "0",
                "trades": None,
                "liquidity": "0",
                "implied_volatility": None,
                "timestamp": "2026-07-10T15:00:00-03:00",
                "source": "provider-test",
                "data_confidence": "0,90",
            }
        )
        item = snapshot.opportunity
        self.assertEqual(item.spot_price, Decimal("30.00"))
        self.assertEqual(item.premium, Decimal("1.40"))
        self.assertEqual(item.volume, 0)
        self.assertEqual(item.liquidity, Decimal("0"))
        self.assertNotIn("volume", snapshot.missing_fields)
        self.assertNotIn("liquidity", snapshot.missing_fields)
        self.assertIn("trades", snapshot.missing_fields)
        self.assertIn("implied_volatility", snapshot.missing_fields)
        self.assertEqual(item.source, "provider-test")
        self.assertEqual(item.timestamp.utcoffset().total_seconds(), 0)

    def test_rejects_boolean_as_numeric_value(self):
        with self.assertRaises(EngineContractError):
            normalize_market_snapshot(
                {
                    "asset": "PETR4",
                    "option_code": "PETRT280",
                    "option_type": "PUT",
                    "expiry": "2026-08-21",
                    "spot_price": True,
                }
            )

    def test_rejects_timestamp_without_timezone(self):
        with self.assertRaises(EngineContractError):
            normalize_market_snapshot(
                {
                    "asset": "PETR4",
                    "option_code": "PETRT280",
                    "option_type": "PUT",
                    "expiry": "2026-08-21",
                    "timestamp": "2026-07-10T15:00:00",
                }
            )
