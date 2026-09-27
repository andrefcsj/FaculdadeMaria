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
    closures: Mapping[str, Mapping[str, object]] | None = None,
    selected_month: str = "",
    selected_year: str = "",
    selected_asset: str = "",
    start_date: str = "",
    end_date: str = "",
    period: str = "",
) -> dict[str, object]:
    """Deriva créditos de venda e o caixa líquido após o encerramento.

    ``gross`` preserva o crédito bruto que ocorreu na abertura. ``net`` é o
    resultado que permaneceu no caixa da operação: em uma recompra, usa o
    resultado realizado, que já inclui o débito de recompra e eventuais custos
    de fechamento importados da nota. Exercícios mantêm somente o prêmio da
    opção — a movimentação das ações não deve inflar este relatório.
    """
    contract_size = _number(legacy.load_config().get("Tamanho contrato opcoes", 100), 100)
    closures = closures or {}
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
        opening_net = _number(operation.get("Premio_liquido"), gross)
        if gross <= 0:
            continue
        operation_id = str(operation.get("ID", ""))
        closure = closures.get(operation_id, {})
        is_closed = str(operation.get("Status", "")).strip().lower() == "encerrada"
        method = str(closure.get("method", "")).strip().lower()
        # Resultado_realizado é a fonte de verdade em recompras: ele é o
        # prêmio líquido de abertura menos recompra e custos de fechamento.
        # Em exercício, o resultado pode incluir a liquidação das ações e não
        # pertence ao relatório de prêmios; em cancelamento não há caixa retido.
        if method == "recompra":
            net = _number(operation.get("Resultado_realizado"))
        elif method == "cancelada":
            net = 0.0
        elif is_closed and not method:
            # Registros históricos sem metadados de fechamento mantêm a
            # compatibilidade usando o resultado já gravado.
            net = _number(operation.get("Resultado_realizado"))
        else:
            net = opening_net
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
            "opening_net": opening_net,
            "status": "Encerrada" if is_closed else "Aberta",
            "close_method": method,
            "close_date": str(closure.get("close_date", "")),
        })

    months = tuple(sorted({row["month"] for row in candidates}, reverse=True))
    years = tuple(sorted({row["year"] for row in candidates}, reverse=True))
    assets = tuple(sorted({row["asset"] for row in candidates}))
    selected_asset = selected_asset.strip().upper()
    period = period or ("range" if start_date or end_date else "month" if selected_month else "year" if selected_year else "all")
    errors = []
    if period not in {"all", "month", "year", "range"}:
        errors.append("Selecione um período válido.")
    effective_month = selected_month if period == "month" else ""
    effective_year = selected_year if period == "year" else ""
    start_date = start_date if period == "range" else ""
    end_date = end_date if period == "range" else ""
    if period == "month":
        try:
            parsed_month = date.fromisoformat(effective_month + "-01")
            if parsed_month.strftime("%Y-%m") != effective_month:
                raise ValueError
        except ValueError:
            errors.append("Selecione um mês válido.")
    if period == "year" and (len(effective_year) != 4 or not effective_year.isascii() or not effective_year.isdigit() or int(effective_year) < 1):
        errors.append("Selecione um ano válido.")
    for value, label in ((start_date, "inicial"), (end_date, "final")):
        if value:
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError
            except ValueError:
                errors.append(f"Informe uma data {label} válida.")
    if period == "range" and not start_date and not end_date:
        errors.append("Informe a data inicial ou final do intervalo.")
    if not errors and start_date and end_date and start_date > end_date:
        errors.append("A data final deve ser igual ou posterior à data inicial.")
    rows = [
        row for row in candidates
        if not errors
        and (not selected_asset or row["asset"] == selected_asset)
        and (not effective_month or row["month"] == effective_month)
        and (not effective_year or row["year"] == effective_year)
        and (not start_date or row["date"] >= start_date)
        and (not end_date or row["date"] <= end_date)
    ]
    rows.sort(key=lambda row: (row["date"], row["option_code"]), reverse=True)
    return {
        "rows": tuple(rows),
        "assets": assets,
        "selected_asset": selected_asset,
        "start_date": start_date,
        "end_date": end_date,
        "period": period,
        "errors": errors,
        "months": months,
        "years": years,
        "selected_month": effective_month,
        "selected_year": effective_year,
        "total_quantity": sum(int(row["quantity"]) for row in rows),
        "total_gross": sum(float(row["gross"]) for row in rows),
        "total_opening_net": sum(float(row["opening_net"]) for row in rows),
        "total_net": sum(float(row["net"]) for row in rows),
    }
