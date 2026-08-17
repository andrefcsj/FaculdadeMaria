from datetime import date
from decimal import Decimal

from engine import OptionOpportunity
from services.covered_call_scanner_service import scan_covered_calls


def option(code: str, *, strike: str, premium: str = "0.50") -> OptionOpportunity:
    return OptionOpportunity(
        asset="PETR4", option_code=code, option_type="CALL", expiry=date(2026, 9, 18),
        spot_price=Decimal("32"), strike=Decimal(strike), premium=Decimal(premium),
        liquidity=Decimal("25000"), source="test",
    )


def test_scanner_uses_only_free_shares_and_preserves_adjusted_average():
    holdings = [{
        "asset": "PETR4", "available_quantity": 250,
        "adjusted_average_price": 33,
    }]
    cards = scan_covered_calls(
        [option("PETRI320", strike="32"), option("PETRI340", strike="34")],
        holdings, as_of=date(2026, 8, 17),
    )
    assert [card.option_code for card in cards] == ["PETRI340"]
    assert cards[0].contracts == 2
    assert cards[0].available_quantity == 250


def test_scanner_requires_one_full_contract_of_coverage():
    holdings = [{"asset": "PETR4", "available_quantity": 99, "adjusted_average_price": 30}]
    assert scan_covered_calls(
        [option("PETRI340", strike="34")], holdings, as_of=date(2026, 8, 17),
    ) == ()
