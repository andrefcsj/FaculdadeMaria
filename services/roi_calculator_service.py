"""Cálculos determinísticos da grade de venda de opções."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from engine import OptionOpportunity
from services.exercise_probability_service import estimate_exercise_probability


@dataclass(frozen=True, slots=True)
class RoiOptionRow:
    option_code: str
    option_type: str
    expiry: date
    business_days: int
    spot: Decimal
    strike: Decimal
    premium: Decimal
    bid: Decimal | None
    ask: Decimal | None
    roi_pct: Decimal
    strike_distance_pct: Decimal
    exercise_probability_pct: Decimal | None
    exercise_probability_label: str
    volume: int


def business_days_until(start: date, end: date) -> int:
    """Conta dias de segunda a sexta após a data inicial, até o vencimento."""
    if end <= start:
        return 0
    current = start + timedelta(days=1)
    total = 0
    while current <= end:
        if current.weekday() < 5:
            total += 1
        current += timedelta(days=1)
    return total


def build_roi_option_rows(
    opportunities: Iterable[OptionOpportunity], *, option_type: str,
    as_of: date | None = None, max_business_days: int = 60,
) -> tuple[RoiOptionRow, ...]:
    selected_type = str(option_type or "").upper()
    if selected_type not in {"PUT", "CALL"}:
        raise ValueError("Selecione CALL ou PUT.")
    reference = as_of or date.today()
    rows = []
    for option in opportunities:
        if option.option_type != selected_type or option.spot_price is None or option.strike is None:
            continue
        dte = business_days_until(reference, option.expiry)
        if dte < 0 or dte > max_business_days:
            continue
        premium = option.bid if option.bid is not None and option.bid > 0 else option.premium
        if premium is None or premium <= 0:
            continue
        capital_base = option.strike if selected_type == "PUT" else option.spot_price
        roi = premium / capital_base * Decimal("100")
        distance = (option.strike / option.spot_price - Decimal("1")) * Decimal("100")
        probability = None
        probability_label = "Indisponível"
        if option.implied_volatility is not None and option.implied_volatility > 0:
            estimate = estimate_exercise_probability(
                option_type=selected_type, spot_price=option.spot_price,
                strike=option.strike, days_to_expiry=max((option.expiry - reference).days, 0),
                annual_volatility=option.implied_volatility,
            )
            probability = estimate.probability * Decimal("100") if estimate.probability is not None else None
            probability_label = estimate.label
        rows.append(RoiOptionRow(
            option_code=option.option_code, option_type=selected_type,
            expiry=option.expiry, business_days=dte, spot=option.spot_price,
            strike=option.strike, premium=premium, bid=option.bid, ask=option.ask,
            roi_pct=roi, strike_distance_pct=distance,
            exercise_probability_pct=probability,
            exercise_probability_label=probability_label,
            volume=int(option.volume or 0),
        ))
    return tuple(sorted(rows, key=lambda row: (row.expiry, row.strike, row.option_code)))
