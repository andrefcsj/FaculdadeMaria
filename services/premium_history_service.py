"""Histórico consultável dos prêmios recebidos nas vendas de opções."""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _opened_at(legacy: Any, operation: Mapping[str, object]) -> date | None:
    return legacy.parse_date(str(operation.get("Data abertura", "")))


def _underlying(legacy: Any, operation: Mapping[str, object]) -> str:
    explicit = str(operation.get("Ativo_subjacente") or "").strip().upper()
    return explicit or legacy.infer_acao_from_option(str(operation.get("Ativo", "")))


def build_premium_history(
    legacy: Any,
    operations: Sequence[Mapping[str, object]],
    *,
    selected_month: str = "",
    selected_year: str = "",
) -> dict[str, object]:
    """Deriva o relatório diretamente das operações, sem duplicar persistência."""
    contract_size = _number(legacy.load_config().get("Tamanho contrato opcoes", 100), 100)
    candidates = []
    for operation in operations:
        strategy = str(operation.get("Estratégia", "Venda")).strip().lower()
        opened_at = _opened_at(legacy, operation)
        if strategy == "compra" or opened_at is None:
            continue
        contracts = _number(operation.get("Contratos_n", operation.get("Contratos")), 0)
        quantity = int(contracts * contract_size)
        gross = _number(operation.get("Premio_bruto"))
        if not gross:
            gross = _number(operation.get("Premio_opcao_n", operation.get("Premio_opcao"))) * quantity
        net = _number(operation.get("Premio_liquido"), gross)
        if gross <= 0:
            continue
        asset = _underlying(legacy, operation)
        candidates.append({
            "date": opened_at.isoformat(),
            "month": opened_at.strftime("%Y-%m"),
            "year": str(opened_at.year),
            "option_code": str(operation.get("Ativo", "")).upper(),
            "asset": asset,
            "logo_url": f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{asset}.png",
            "quantity": quantity,
            "gross": gross,
            "net": net,
        })

    months = tuple(sorted({row["month"] for row in candidates}, reverse=True))
    years = tuple(sorted({row["year"] for row in candidates}, reverse=True))
    effective_month = selected_month if selected_month in months else ""
    effective_year = selected_year if selected_year in years else ""
    rows = [
        row for row in candidates
        if (not effective_month or row["month"] == effective_month)
        and (effective_month or not effective_year or row["year"] == effective_year)
    ]
    rows.sort(key=lambda row: (row["date"], row["option_code"]), reverse=True)
    return {
        "rows": tuple(rows),
        "months": months,
        "years": years,
        "selected_month": effective_month,
        "selected_year": effective_year,
        "total_quantity": sum(int(row["quantity"]) for row in rows),
        "total_gross": sum(float(row["gross"]) for row in rows),
        "total_net": sum(float(row["net"]) for row in rows),
    }
