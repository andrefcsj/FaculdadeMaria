"""Estimativa explicável de exercício baseada em volatilidade histórica observada.

A estimativa não é promessa nem probabilidade garantida. Quando não há histórico
suficiente, o serviço retorna indisponível em vez de inventar volatilidade.
"""
from __future__ import annotations

import json
import math
import statistics
import time
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ExerciseProbabilityEstimate:
    probability: Decimal | None
    label: str
    confidence: str
    methodology: str
    annual_volatility: Decimal | None = None
    spot_price: Decimal | None = None

    @property
    def percentage(self) -> str:
        if self.probability is None:
            return "--"
        return f"{(self.probability * Decimal('100')).quantize(Decimal('0.1'))}%".replace(".", ",")


_CACHE: dict[str, tuple[float, tuple[Decimal | None, tuple[Decimal, ...]]]] = {}
_CACHE_SECONDS = 30 * 60


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def annualized_historical_volatility(closes: Iterable[Decimal]) -> Decimal | None:
    values = [float(value) for value in closes if value is not None and value > 0]
    if len(values) < 30:
        return None
    returns = [math.log(values[index] / values[index - 1]) for index in range(1, len(values))]
    if len(returns) < 2:
        return None
    volatility = statistics.stdev(returns) * math.sqrt(252)
    if not math.isfinite(volatility) or volatility <= 0:
        return None
    return Decimal(str(volatility))


def estimate_exercise_probability(
    *,
    option_type: str,
    spot_price: Decimal,
    strike: Decimal,
    days_to_expiry: int,
    annual_volatility: Decimal,
) -> ExerciseProbabilityEstimate:
    """Calcula chance estatística de terminar ITM sob modelo lognormal de deriva zero."""
    if spot_price <= 0 or strike <= 0:
        raise ValueError("Spot e strike devem ser positivos.")
    if annual_volatility <= 0:
        raise ValueError("Volatilidade anual deve ser positiva.")

    if days_to_expiry <= 0:
        if option_type.upper() == "PUT":
            probability = Decimal("1") if spot_price < strike else Decimal("0") if spot_price > strike else Decimal("0.5")
        else:
            probability = Decimal("1") if spot_price > strike else Decimal("0") if spot_price < strike else Decimal("0.5")
    else:
        years = days_to_expiry / 365.0
        sigma = float(annual_volatility)
        denominator = sigma * math.sqrt(years)
        z = (math.log(float(strike / spot_price)) + 0.5 * sigma * sigma * years) / denominator
        put_probability = _normal_cdf(z)
        raw_probability = put_probability if option_type.upper() == "PUT" else 1.0 - put_probability
        probability = Decimal(str(min(max(raw_probability, 0.0), 1.0)))

    if probability >= Decimal("0.65"):
        label = "Alta"
    elif probability >= Decimal("0.35"):
        label = "Moderada"
    else:
        label = "Baixa"

    return ExerciseProbabilityEstimate(
        probability=probability,
        label=label,
        confidence="Estatística",
        methodology="Estimativa com volatilidade histórica anualizada e modelo lognormal de deriva zero; não é garantia de exercício.",
        annual_volatility=annual_volatility,
        spot_price=spot_price,
    )


def _fetch_yahoo_history(ticker: str) -> tuple[Decimal | None, tuple[Decimal, ...]]:
    now = time.time()
    cached = _CACHE.get(ticker)
    if cached and now - cached[0] < _CACHE_SECONDS:
        return cached[1]

    symbol = ticker if ticker.endswith(".SA") else f"{ticker}.SA"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=4) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("chart", {}).get("result", [])
    if not results:
        raise ValueError("Histórico indisponível.")
    result = results[0]
    meta = result.get("meta", {})
    regular_price = meta.get("regularMarketPrice")
    closes_raw = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    closes = tuple(Decimal(str(value)) for value in closes_raw if value not in (None, 0))
    spot = Decimal(str(regular_price)) if regular_price not in (None, 0) else (closes[-1] if closes else None)
    output = (spot, closes)
    _CACHE[ticker] = (now, output)
    return output


def estimate_operation_exercise_probability(
    *,
    ticker: str,
    option_type: str,
    strike: Decimal,
    expiry: date | None,
    as_of: date | None = None,
) -> ExerciseProbabilityEstimate:
    as_of = as_of or date.today()
    if not ticker or expiry is None or strike <= 0:
        return ExerciseProbabilityEstimate(None, "Indisponível", "Dados insuficientes", "Cotação, strike ou vencimento ausente.")
    try:
        spot, closes = _fetch_yahoo_history(ticker)
        volatility = annualized_historical_volatility(closes)
        if spot is None or volatility is None:
            return ExerciseProbabilityEstimate(None, "Indisponível", "Dados insuficientes", "Histórico insuficiente para estimar sem inventar volatilidade.", spot_price=spot)
        return estimate_exercise_probability(
            option_type=option_type,
            spot_price=spot,
            strike=strike,
            days_to_expiry=max((expiry - as_of).days, 0),
            annual_volatility=volatility,
        )
    except Exception:
        return ExerciseProbabilityEstimate(None, "Indisponível", "Fonte indisponível", "Não foi possível obter histórico suficiente; nenhuma probabilidade foi inventada.")
