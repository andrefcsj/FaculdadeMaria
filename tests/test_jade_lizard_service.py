from services.jade_lizard_service import JadeConfig, scan_estimated_chain


def test_scanner_only_returns_jades_that_pass_the_main_rules():
    rows = scan_estimated_chain(["PETR4", "VALE3"], {"PETR4": 37.0, "VALE3": 62.0}.get)

    assert rows
    assert all(-0.30 <= row.put_delta <= -0.15 for row in rows)
    assert all(15 <= row.days <= 45 for row in rows)
    assert all(row.retention_pct >= 95 for row in rows)
    assert all(row.score >= 80 for row in rows)
    assert all(row.long_call_strike > row.short_call_strike for row in rows)


def test_scanner_discards_everything_when_score_threshold_is_unreachable():
    rows = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get, JadeConfig(min_score=101))

    assert rows == []


def test_financial_identity_and_capital_are_consistent():
    row = scan_estimated_chain(["PETR4"], {"PETR4": 37.0}.get)[0]

    expected_credit = row.put_credit + row.short_call_credit - row.long_call_debit
    assert abs(row.net_credit - expected_credit) <= 0.02
    assert row.break_even == row.effective_cost
    assert abs(row.max_profit - row.net_credit * 100) <= 0.51
    assert row.capital_required == row.max_loss
