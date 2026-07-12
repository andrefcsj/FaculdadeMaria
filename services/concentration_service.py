"""Deterministic portfolio concentration calculations for cash-secured PUTs."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping

MAX_ASSET_CONCENTRATION = Decimal("0.35")
ATTENTION_ASSET_CONCENTRATION = Decimal("0.25")


def underlying_from_option(option_code: object) -> str:
    letters = "".join(character for character in str(option_code or "").upper() if character.isalpha())
    return letters[:4] if letters else "N/D"


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


@dataclass(frozen=True, slots=True)
class PortfolioConcentration:
    allocated_by_asset: Mapping[str, Decimal]
    total_capital: Decimal

    def projected_share(self, asset: str, incremental_capital: Decimal) -> Decimal | None:
        incremental = max(incremental_capital, Decimal("0"))
        denominator = max(self.total_capital, sum(self.allocated_by_asset.values()) + incremental)
        if denominator <= 0:
            return None
        current = self.allocated_by_asset.get(underlying_from_option(asset), Decimal("0"))
        return min((current + incremental) / denominator, Decimal("1"))


def build_portfolio_concentration(
    operations: Iterable[Mapping[str, object]], total_capital: object
) -> PortfolioConcentration:
    allocated: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for operation in operations:
        if str(operation.get("Status", "")).lower() != "aberta" or str(operation.get("Tipo", "PUT")).upper() != "PUT":
            continue
        asset = underlying_from_option(operation.get("Ativo"))
        allocated[asset] += max(_decimal(operation.get("Capital")), Decimal("0"))
    return PortfolioConcentration(dict(allocated), max(_decimal(total_capital), Decimal("0")))


def concentration_reading(share: Decimal | None) -> tuple[str, str, str]:
    if share is None:
        return "unknown", "Não calculada", "Informe o capital total para avaliar concentração."
    if share > MAX_ASSET_CONCENTRATION:
        return "high", "Concentração alta", "A nova posição ultrapassa o limite de 35% do capital por ativo."
    if share >= ATTENTION_ASSET_CONCENTRATION:
        return "attention", "Atenção", "A exposição projetada está próxima do limite por ativo."
    return "balanced", "Equilibrada", "A exposição projetada permanece dentro da política por ativo."
