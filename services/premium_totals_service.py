"""Totais de prêmios recebidos e efetivamente retidos nas vendas de opções."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping, Sequence


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def calculate_premium_totals(
    operations: Sequence[Mapping[str, object]],
    closures: Mapping[str, Mapping[str, object]],
    *,
    contract_size: Decimal = Decimal("100"),
) -> tuple[Decimal, Decimal]:
    """Retorna ``(recebido_na_abertura, retido_apos_encerramentos)``."""
    received_total = Decimal("0")
    retained_total = Decimal("0")
    for operation in operations:
        strategy = str(operation.get("Estratégia", "Venda")).strip().lower()
        option_type = str(operation.get("Tipo", "")).strip().upper()
        if strategy == "compra" or option_type not in {"PUT", "CALL"}:
            continue

        contracts = _decimal(operation.get("Contratos_n", operation.get("Contratos")))
        net_premium = _decimal(operation.get("Premio_liquido"))
        if "Premio_liquido" not in operation:
            gross = _decimal(operation.get("Premio_opcao_n", operation.get("Premio_opcao"))) * contracts * contract_size
            net_premium = gross - _decimal(operation.get("Custos")) - _decimal(operation.get("IRRF"))
        received_total += net_premium

        if str(operation.get("Status", "")).strip().lower() != "encerrada":
            retained_total += net_premium
            continue

        metadata = closures.get(str(operation.get("ID", "")), {})
        method = str(metadata.get("method", "")).strip().lower()
        if method == "recompra":
            retained_total += net_premium - _decimal(metadata.get("repurchase_value")) * contracts * contract_size
        elif method == "cancelada":
            continue
        elif method in {"exercida", "virou_po"}:
            retained_total += net_premium
        else:
            # Compatibilidade com encerramentos antigos, anteriores aos
            # metadados que identificam recompra, exercício e expiração.
            retained_total += _decimal(operation.get("Resultado_realizado"))

    return received_total, retained_total
