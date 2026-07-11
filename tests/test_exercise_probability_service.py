from datetime import date
from decimal import Decimal

import pytest

from services.exercise_probability_service import (
    annualized_historical_volatility,
    estimate_exercise_probability,
)


def test_historical_volatility_requires_sufficient_history():
    assert annualized_historical_volatility([Decimal("10")] * 29) is None


def test_put_probability_is_high_when_strike_is_well_above_spot():
    estimate = estimate_exercise_probability(
        option_type="PUT",
        spot_price=Decimal("20"),
        strike=Decimal("25"),
        days_to_expiry=30,
        annual_volatility=Decimal("0.25"),
    )
    assert estimate.probability is not None
    assert estimate.probability > Decimal("0.65")
    assert estimate.label == "Alta"


def test_put_probability_is_low_when_strike_is_well_below_spot():
    estimate = estimate_exercise_probability(
        option_type="PUT",
        spot_price=Decimal("25"),
        strike=Decimal("20"),
        days_to_expiry=30,
        annual_volatility=Decimal("0.25"),
    )
    assert estimate.probability is not None
    assert estimate.probability < Decimal("0.35")
    assert estimate.label == "Baixa"


def test_expiry_probability_uses_intrinsic_condition():
    estimate = estimate_exercise_probability(
        option_type="PUT",
        spot_price=Decimal("18"),
        strike=Decimal("20"),
        days_to_expiry=0,
        annual_volatility=Decimal("0.25"),
    )
    assert estimate.probability == Decimal("1")


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        estimate_exercise_probability(
            option_type="PUT",
            spot_price=Decimal("0"),
            strike=Decimal("20"),
            days_to_expiry=30,
            annual_volatility=Decimal("0.25"),
        )
