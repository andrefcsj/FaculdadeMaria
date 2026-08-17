"""Scanner de CALL coberta restrito às ações livres da carteira real."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from engine import OptionOpportunity


@dataclass(frozen=True, slots=True)
class CoveredCallCard:
    asset: str
    option_code: str
    spot: Decimal
    strike: Decimal
    premium: Decimal
    expiry: date
    dte: int
    available_quantity: int
    contracts: int
    adjusted_average: Decimal
    premium_yield: Decimal
    upside: Decimal
    effective_sale_price: Decimal
    score: int


def scan_covered_calls(
    opportunities: Iterable[OptionOpportunity], holdings: Iterable[dict], *, as_of: date | None = None,
) -> tuple[CoveredCallCard, ...]:
    """Prioriza CALLs OTM que preservam o PM e possuem cobertura disponível."""
    as_of = as_of or date.today()
    portfolio = {
        str(item.get("asset", "")).upper(): item
        for item in holdings
        if int(item.get("available_quantity", 0) or 0) >= 100
    }
    cards: list[CoveredCallCard] = []
    for option in opportunities:
        holding = portfolio.get(option.asset.upper())
        if option.option_type != "CALL" or holding is None or option.expiry < as_of:
            continue
        dte = (option.expiry - as_of).days
        average = Decimal(str(holding.get("adjusted_average_price", holding.get("tax_cost_per_share", 0)) or 0))
        if not 7 <= dte <= 60 or option.premium <= 0 or option.spot_price <= 0:
            continue
        # Evita sugerir entrega abaixo do custo ajustado ou CALL já dentro do dinheiro.
        if option.strike < max(average, option.spot_price):
            continue
        available = int(holding.get("available_quantity", 0) or 0)
        contracts = available // 100
        premium_yield = option.premium / option.spot_price
        upside = option.strike / option.spot_price - Decimal("1")
        annualized_yield = premium_yield * Decimal("365") / Decimal(max(dte, 1))
        liquidity = min(Decimal(str(option.liquidity or 0)) / Decimal("50000"), Decimal("1"))
        score = min(100, max(0, int(annualized_yield * 120 + upside * 180 + liquidity * 20)))
        cards.append(CoveredCallCard(
            asset=option.asset, option_code=option.option_code, spot=option.spot_price,
            strike=option.strike, premium=option.premium, expiry=option.expiry, dte=dte,
            available_quantity=available, contracts=contracts, adjusted_average=average,
            premium_yield=premium_yield, upside=upside,
            effective_sale_price=option.strike + option.premium, score=score,
        ))
    return tuple(sorted(cards, key=lambda item: (-item.score, item.dte, item.option_code)))
