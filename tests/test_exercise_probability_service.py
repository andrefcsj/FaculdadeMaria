from decimal import Decimal

from services.exercise_probability_service import annualized_historical_volatility, estimate_exercise_probability


def test_probability_is_bounded_for_put():
    result = estimate_exercise_probability(
        option_type="PUT",
        spot_price=Decimal("20"),
        strike=Decimal("19"),
        days_to_expiry=30,
        annual_volatility=Decimal("0.30"),
    )
    assert Decimal("0") <= result.probability <= Decimal("1")
    assert result.label in {"Baixa", "Moderada", "Alta"}


def test_probability_increases_when_put_strike_is_higher():
    low = estimate_exercise_probability(option_type="PUT", spot_price=Decimal("20"), strike=Decimal("18"), days_to_expiry=30, annual_volatility=Decimal("0.30"))
    high = estimate_exercise_probability(option_type="PUT", spot_price=Decimal("20"), strike=Decimal("22"), days_to_expiry=30, annual_volatility=Decimal("0.30"))
    assert high.probability > low.probability


def test_historical_volatility_requires_enough_data():
    assert annualized_historical_volatility([Decimal("10")] * 10) is None
