from datetime import date, timedelta

from services.jade_lizard_service import (
    JadeConfig,
    build_estimated_option_code,
    is_dte_allowed,
    scan_estimated_chain,
)


def test_scanner_only_returns_jades_that_pass_the_main_rules():
    rows = scan_estimated_chain(["PETR4", "VALE3"], {"PETR4": 37.0, "VALE3": 62.0}.get)

    assert rows
    assert all(-0.30 <= row.put_delta <= -0.15 for row in rows)
    assert all(15 <= row.days <= 45 for row in rows)
    assert all(row.retention_pct >= 95 for row in rows)
    assert all(row.net_credit >= row.spread_width for row in rows)
    assert all(row.score >= 80 for row in rows)
    assert all(row.long_call_strike > row.short_call_strike for row in rows)
    assert all(row.put_roi_on_strike == round(row.put_credit / row.put_strike * 100, 2) for row in rows)
    assert all(row.jade_roi_on_strike == round(row.net_credit / row.put_strike * 100, 2) for row in rows)
    assert all(row.logo_url.endswith(f"/{row.ticker}.png") for row in rows)


def test_scanner_discards_everything_when_score_threshold_is_unreachable():
    rows = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get, JadeConfig(min_score=101))

    assert rows == []


def test_expiry_window_is_a_hard_filter_with_inclusive_45_day_limit():
    assert is_dte_allowed(15)
    assert is_dte_allowed(45)
    assert not is_dte_allowed(46)
    assert not is_dte_allowed(14)

    rows = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get, JadeConfig(max_dte=29))
    assert rows == []


def test_option_codes_follow_b3_type_and_expiry_month():
    assert build_estimated_option_code("PETR4", "call", 40, date(2026, 4, 17)) == "PETRD4000"
    assert build_estimated_option_code("PETR4", "put", 40, date(2026, 4, 17)) == "PETRP4000"
    assert build_estimated_option_code("B3SA3", "call", 12.5, date(2026, 9, 18)) == "B3SAI1250"
    assert build_estimated_option_code("B3SA3", "put", 12.5, date(2026, 9, 18)) == "B3SAU1250"


def test_all_jade_legs_use_codes_for_the_same_expiry_month():
    row = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get)[0]
    month = date.fromisoformat(row.expiry).month

    assert row.put_code[4] == "MNOPQRSTUVWX"[month - 1]
    assert row.short_call_code[4] == "ABCDEFGHIJKL"[month - 1]
    assert row.long_call_code[4] == "ABCDEFGHIJKL"[month - 1]


def test_financial_identity_and_capital_are_consistent():
    row = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get)[0]

    expected_credit = row.put_credit + row.short_call_credit - row.long_call_debit
    assert abs(row.net_credit - expected_credit) <= 0.02
    assert row.break_even == row.effective_cost
    assert abs(row.max_profit - row.net_credit * 100) <= 0.51
    assert row.capital_required == row.max_loss
    assert row.capital_required == round((row.put_strike - row.net_credit) * 100, 2)


def test_scanner_uses_the_selected_projected_expiry():
    target = date.today() + timedelta(days=22)
    rows = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get, target_expiry=target)

    assert rows
    assert all(row.expiry == target.isoformat() and row.days == 22 for row in rows)


def test_scanner_only_recommends_structures_without_upside_loss_at_expiry():
    rows = scan_estimated_chain(["PETR4", "VALE3"], {"PETR4": 37.0, "VALE3": 62.0}.get)

    assert rows
    for row in rows:
        upside_result_per_share = row.net_credit - row.spread_width
        assert upside_result_per_share >= 0
