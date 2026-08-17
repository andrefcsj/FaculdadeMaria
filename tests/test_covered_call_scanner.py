from datetime import date
from decimal import Decimal

from engine import OptionOpportunity
from services.covered_call_scanner_service import scan_covered_calls


def option(code: str, *, strike: str, premium: str = "0.50", expiry=date(2026, 9, 18)) -> OptionOpportunity:
    return OptionOpportunity(
        asset="PETR4", option_code=code, option_type="CALL", expiry=expiry,
        spot_price=Decimal("32"), strike=Decimal(strike), premium=Decimal(premium),
        liquidity=Decimal("25000"), source="test",
    )


def test_scanner_uses_portfolio_shares_and_preserves_adjusted_average():
    holdings = [{
        "asset": "PETR4", "quantity": 250, "available_quantity": 250,
        "adjusted_average_price": 33,
    }]
    cards = scan_covered_calls(
        [option("PETRI320", strike="32"), option("PETRI340", strike="34")],
        holdings, as_of=date(2026, 8, 17),
    )
    assert [card.option_code for card in cards] == ["PETRI340"]
    assert cards[0].contracts == 2
    assert cards[0].available_quantity == 250


def test_scanner_requires_one_full_contract_in_portfolio():
    holdings = [{"asset": "PETR4", "quantity": 99, "available_quantity": 99, "adjusted_average_price": 30}]
    assert scan_covered_calls(
        [option("PETRI340", strike="34")], holdings, as_of=date(2026, 8, 17),
    ) == ()


def test_scanner_includes_one_day_expiry_and_stops_at_45_days():
    holdings = [{"asset": "PETR4", "quantity": 100, "available_quantity": 100, "adjusted_average_price": 30}]
    cards = scan_covered_calls([
        option("PETRH341", strike="34", expiry=date(2026, 8, 18)),
        option("PETRH340", strike="34", expiry=date(2026, 8, 17)),
        option("PETRJ345", strike="34", expiry=date(2026, 10, 1)),
        option("PETRJ346", strike="34", expiry=date(2026, 10, 2)),
    ], holdings, as_of=date(2026, 8, 17))
    assert {card.dte for card in cards} == {1, 45}


def test_scanner_keeps_asset_with_existing_call_for_replacement():
    holdings = [{
        "asset": "PETR4", "quantity": 200, "covered_quantity": 200,
        "available_quantity": 0, "adjusted_average_price": 30,
    }]
    cards = scan_covered_calls(
        [option("PETRI340", strike="34")], holdings, as_of=date(2026, 8, 17),
    )
    assert len(cards) == 1
    assert cards[0].contracts == 2
    assert cards[0].replacement_required is True
