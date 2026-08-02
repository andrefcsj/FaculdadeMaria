from decimal import Decimal

from services.option_cycle_service import build_cycle_groups, classify_option_cycle


def test_weekly_suffix_identifies_week_number_case_insensitively():
    assert classify_option_cycle("WEGET464W1") == {
        "is_weekly": True,
        "cycle": "weekly",
        "week_number": 1,
        "cycle_label": "Semanal · 1ª semana",
    }
    assert classify_option_cycle("abcde99w5")["week_number"] == 5


def test_non_terminal_or_invalid_week_marker_remains_monthly():
    assert classify_option_cycle("WEGET464")["cycle"] == "monthly"
    assert classify_option_cycle("WEGW1X")["cycle"] == "monthly"
    assert classify_option_cycle("WEGET464W6")["cycle"] == "monthly"


def test_cycle_roi_is_weighted_by_capital():
    rows = [
        {"cycle": "weekly", "result": "10", "capital": "100"},
        {"cycle": "weekly", "result": "10", "capital": "900"},
        {"cycle": "monthly", "result": "30", "capital": "1000"},
    ]
    groups = build_cycle_groups(rows, result_key="result", capital_key="capital")
    monthly, weekly = groups
    assert monthly["roi"] == Decimal("3")
    assert weekly["roi"] == Decimal("2")
