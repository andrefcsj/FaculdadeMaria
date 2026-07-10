import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from engine.core import OptionOpportunity
from engine.errors import EngineContractError


class EngineContractTests(unittest.TestCase):
    def test_contract_preserves_zero_and_reports_missing_fields(self):
        opportunity = OptionOpportunity(
            asset="PETR4",
            option_code="PETRT280",
            option_type="put",
            expiry=date(2026, 8, 21),
            spot_price=Decimal("30"),
            strike=Decimal("28"),
            premium=Decimal("0"),
            volume=0,
            timestamp=datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(opportunity.option_type, "PUT")
        self.assertEqual(opportunity.premium, Decimal("0"))
        self.assertEqual(opportunity.volume, 0)
        self.assertNotIn("premium", opportunity.missing_fields())
        self.assertNotIn("volume", opportunity.missing_fields())
        self.assertIn("bid", opportunity.missing_fields())

    def test_contract_rejects_invalid_option_type(self):
        with self.assertRaises(EngineContractError):
            OptionOpportunity(
                asset="PETR4",
                option_code="PETRX",
                option_type="FUTURE",
                expiry=date(2026, 8, 21),
            )

    def test_contract_requires_timezone_aware_timestamp(self):
        with self.assertRaises(EngineContractError):
            OptionOpportunity(
                asset="PETR4",
                option_code="PETRT280",
                option_type="PUT",
                expiry=date(2026, 8, 21),
                timestamp=datetime(2026, 7, 10, 15, 0),
            )
