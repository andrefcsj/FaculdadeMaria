from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from engine import OptionOpportunity
from services.roi_calculator_service import business_days_until, build_roi_option_rows, option_cycle


ROOT = Path(__file__).parents[1]


def opportunity(*, option_type="PUT", expiry=date(2026, 9, 18), strike="14", bid="0.70", iv="0.25"):
    return OptionOpportunity(
        asset="CPLE3", option_code="CPLET140" if option_type == "PUT" else "CPLEI140",
        option_type=option_type, expiry=expiry, spot_price=Decimal("14.28"),
        strike=Decimal(strike), premium=Decimal("0.65"), bid=Decimal(bid),
        ask=Decimal("0.75"), volume=1200, implied_volatility=Decimal(iv),
        timestamp=datetime(2026, 8, 24, tzinfo=timezone.utc), source="sldx_api",
    )


def test_business_days_exclude_weekends():
    assert business_days_until(date(2026, 8, 21), date(2026, 8, 24)) == 1


def test_put_roi_uses_bid_over_strike_and_exposes_distance_and_probability():
    row = build_roi_option_rows(
        [opportunity()], option_type="PUT", as_of=date(2026, 8, 24),
    )[0]
    assert row.premium == Decimal("0.70")
    assert row.roi_pct == Decimal("5.00")
    assert row.strike_distance_pct.quantize(Decimal("0.01")) == Decimal("-1.96")
    assert row.exercise_probability_pct is not None


def test_call_roi_uses_bid_over_current_share_price():
    row = build_roi_option_rows(
        [opportunity(option_type="CALL")], option_type="CALL", as_of=date(2026, 8, 24),
    )[0]
    assert row.roi_pct.quantize(Decimal("0.01")) == Decimal("4.90")


def test_options_beyond_sixty_business_days_are_excluded():
    rows = build_roi_option_rows(
        [opportunity(expiry=date(2026, 12, 31))], option_type="PUT", as_of=date(2026, 8, 24),
    )
    assert rows == ()


def test_option_cycle_separates_third_friday_from_weeklies():
    assert option_cycle(date(2026, 9, 18)) == "Mensal"
    assert option_cycle(date(2026, 9, 11)) == "Semanal"


def test_roi_page_and_sidebar_entry_are_available():
    from app import app

    response = app.test_client().get("/calculadora-roi")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Grade de opções" in html
    assert "Atualizar grade pela API" in html
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert base.index("Grade de opções") < base.index("SIMULADOR de Cálculos")


def test_dashboard_portfolio_headers_align_with_numeric_columns():
    css = (ROOT / "static" / "theme.css").read_text(encoding="utf-8")
    assert ".equity-composition__head>span:not(:first-child){text-align:right}" in css
