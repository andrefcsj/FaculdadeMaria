"""Cálculo explícito dos resultados de encerramento de uma operação."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


VALID_CLOSE_METHODS = {"recompra", "exercida", "cancelada", "virou_po"}


@dataclass(frozen=True)
class OperationCloseResult:
    method: str
    status: str
    result: Decimal
    repurchase_total: Decimal


def calculate_operation_close(
    *,
    method: str,
    close_date: date,
    expiry: date | None,
    premium_received: Decimal,
    repurchase_per_unit: Decimal,
    contracts: Decimal,
    contract_size: Decimal,
    position_side: str = "Venda",
) -> OperationCloseResult:
    method = str(method or "").strip().lower()
    if method not in VALID_CLOSE_METHODS:
        raise ValueError("Selecione uma forma válida de encerramento.")
    if contracts <= 0 or contract_size <= 0:
        raise ValueError("Quantidade e tamanho do contrato devem ser positivos.")
    if premium_received < 0 or repurchase_per_unit < 0:
        raise ValueError("Prêmio e recompra não podem ser negativos.")
    if method == "virou_po" and expiry and close_date < expiry:
        raise ValueError("A opção só pode ser marcada como virou pó na data do vencimento ou depois.")

    is_purchase = str(position_side or "").strip().lower() == "compra"
    # O mesmo campo representa a recompra de uma opção vendida ou a venda de
    # uma opção comprada. Em ambos os casos é o caixa do encerramento.
    repurchase_total = repurchase_per_unit * contracts * contract_size if method == "recompra" else Decimal("0")
    if method == "recompra":
        result = repurchase_total - premium_received if is_purchase else premium_received - repurchase_total
    elif method == "cancelada":
        result = Decimal("0")
    elif is_purchase:
        # Uma opção comprada que expira sem valor perde integralmente o débito
        # de entrada. No exercício, o prêmio pago também continua sendo custo;
        # a movimentação das ações é contabilizada separadamente.
        result = -premium_received
    else:
        # Exercício faz parte da estratégia e o prêmio recebido permanece realizado.
        result = premium_received

    return OperationCloseResult(
        method=method,
        status="Encerrada",
        result=result,
        repurchase_total=repurchase_total,
    )
