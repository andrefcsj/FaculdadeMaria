"""Persistência de encerramento e visão executiva de operações fechadas."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from services.option_cycle_service import build_cycle_groups, classify_option_cycle


FIELDS = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]


def _decimal(value: Any) -> Decimal:
    text = str(value or "0").strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text or "0")
    except InvalidOperation as exc:
        raise ValueError(f"Valor inválido: {value}") from exc


def _metadata_path(legacy) -> Path:
    return legacy.DATA / "operation_closures.json"


def load_closure_metadata(legacy) -> dict[str, dict[str, Any]]:
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS operation_closure_metadata (
                operation_id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            conn.commit()
            cur.execute("SELECT operation_id, payload FROM operation_closure_metadata")
            return {str(row[0]): row[1] if isinstance(row[1], dict) else json.loads(row[1]) for row in cur.fetchall()}
        finally:
            conn.close()
    path = _metadata_path(legacy)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def save_closure_metadata(legacy, operation_id: str, *, close_date: date, method: str, repurchase_value: Decimal, result: Decimal) -> None:
    payload = {
        "operation_id": str(operation_id),
        "close_date": close_date.isoformat(),
        "method": str(method),
        "repurchase_value": str(repurchase_value),
        "result": str(result),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS operation_closure_metadata (
                operation_id TEXT PRIMARY KEY, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cur.execute("""INSERT INTO operation_closure_metadata (operation_id,payload) VALUES (%s,%s::jsonb)
                ON CONFLICT (operation_id) DO UPDATE SET payload=EXCLUDED.payload,updated_at=NOW()""", (str(operation_id), json.dumps(payload, ensure_ascii=False)))
            conn.commit()
            return
        finally:
            conn.close()
    rows = load_closure_metadata(legacy)
    rows[str(operation_id)] = payload
    path = _metadata_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def delete_closure_metadata(legacy, operation_id: str) -> None:
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM operation_closure_metadata WHERE operation_id=%s", (str(operation_id),))
            conn.commit()
            return
        finally:
            conn.close()
    rows = load_closure_metadata(legacy)
    rows.pop(str(operation_id), None)
    path = _metadata_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def raw_operation(legacy, operation_id: str):
    rows = legacy.read_csv(legacy.OPERACOES)
    operation = legacy.get_operacao_pg(operation_id) if legacy.USE_POSTGRES else legacy.find_row(rows, operation_id)
    return rows, operation


def persist_operation(legacy, rows, operation: dict[str, Any]) -> None:
    if legacy.USE_POSTGRES:
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""UPDATE operacoes SET ativo=%s,tipo=%s,estrategia=%s,status=%s,contratos=%s,
                strike=%s,premio_opcao=%s,custos=%s,irrf=%s,vencimento=%s,cotacao_atual=%s,resultado_realizado=%s WHERE id=%s""",
                (operation["Ativo"], operation["Tipo"], operation["Estratégia"], operation["Status"], operation["Contratos"], operation["Strike"], operation["Premio_opcao"], operation["Custos"], operation["IRRF"], operation["Vencimento"], operation["Cotacao_atual"], operation["Resultado_realizado"], operation["ID"]))
            conn.commit()
            return
        finally:
            conn.close()
    legacy.write_csv(legacy.OPERACOES, rows, FIELDS)


def delete_operation(legacy, rows, operation_id: str) -> None:
    if legacy.USE_POSTGRES:
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor(); cur.execute("DELETE FROM operacoes WHERE id=%s", (str(operation_id),)); conn.commit()
        finally:
            conn.close()
    else:
        remaining = [row for row in rows if str(row.get("ID")) != str(operation_id)]
        legacy.write_csv(legacy.OPERACOES, remaining, FIELDS)
    from services.operation_preferences_service import delete_operation_preference
    delete_operation_preference(legacy, operation_id)


def serialize_closed_operation(legacy, operation: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    contracts = _decimal(operation.get("Contratos"))
    size = _decimal(legacy.load_config().get("Tamanho contrato opcoes", 100))
    strike = _decimal(operation.get("Strike"))
    premium = _decimal(operation.get("Premio_opcao"))
    costs = _decimal(operation.get("Custos"))
    irrf = _decimal(operation.get("IRRF"))
    capital = contracts * size * strike
    gross_premium = contracts * size * premium
    result = _decimal(operation.get("Resultado_realizado"))
    strategy = str(operation.get("Estratégia", "Venda")).strip().lower()
    method = str(metadata.get("method", "")).strip().lower()
    # Corrige também registros históricos criados antes da distinção entre
    # crédito de venda e débito de compra. Assim, o histórico e a projeção de
    # DARF deixam de tratar uma opção comprada que virou pó como lucro.
    if strategy == "compra" and method in {"recompra", "exercida", "virou_po", "cancelada"}:
        opening_debit = gross_premium + costs + irrf
        if method == "recompra":
            closing_credit = _decimal(metadata.get("repurchase_value", "0")) * contracts * size
            result = closing_credit - opening_debit
        elif method == "cancelada":
            result = Decimal("0")
        else:
            result = -opening_debit
    roi = result / capital * Decimal("100") if capital else Decimal("0")
    close_date = metadata.get("close_date") or operation.get("Data fechamento") or ""
    from services.operation_preferences_service import operation_underlying
    underlying = operation_underlying(legacy, operation)
    underlying_logo = (
        f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{underlying}.png"
        if underlying else ""
    )
    serialized = {
        "ID": str(operation.get("ID", "")), "Ativo": str(operation.get("Ativo", "")),
        "Ativo_subjacente": underlying, "Logo_subjacente": underlying_logo,
        "Tipo": str(operation.get("Tipo", "PUT")), "Estrategia": str(operation.get("Estratégia", "Venda")),
        "Status": str(operation.get("Status", "Encerrada")), "Contratos": str(contracts),
        "Quantidade_acoes": int(contracts * size), "Strike": str(strike), "Premio_opcao": str(premium),
        "Premio_bruto": str(gross_premium), "Custos": str(costs), "IRRF": str(irrf),
        "Vencimento": str(operation.get("Vencimento", "")), "Cotacao_atual": str(operation.get("Cotacao_atual", "0")),
        "Data_abertura": str(operation.get("Data abertura", "")), "Data_fechamento": str(close_date),
        "Metodo_encerramento": str(metadata.get("method", "Não registrado")),
        "Valor_recompra": str(metadata.get("repurchase_value", "0")),
        "Resultado_realizado": str(result), "Capital": str(capital), "ROI_realizado": str(roi),
    }
    serialized.update(classify_option_cycle(operation.get("Ativo")))
    return serialized


def _shift_month(month: str, amount: int) -> str:
    year, number = (int(part) for part in month.split("-"))
    absolute = year * 12 + number - 1 + amount
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def build_darf_projection(closed_operations: list[dict[str, Any]], *, today: date | None = None) -> dict[str, Any]:
    """Estimate DARF 6015 by realization month, preserving separate loss buckets."""
    today = today or date.today()
    current_month = today.strftime("%Y-%m")
    target_months = [_shift_month(current_month, offset) for offset in (-1, 0, 1)]
    monthly: dict[str, dict[str, Any]] = {}

    for operation in closed_operations:
        close_date = str(operation.get("Data_fechamento", ""))
        if len(close_date) < 7:
            continue
        month = close_date[:7]
        bucket = monthly.setdefault(month, {
            "operations": 0, "common_result": Decimal("0"), "day_result": Decimal("0"),
            "common_irrf": Decimal("0"), "day_irrf": Decimal("0"), "review_count": 0,
            "exercise_deferred_count": 0,
            "tax_operation_candidates": [],
        })
        bucket["operations"] += 1
        method = str(operation.get("Metodo_encerramento", "")).lower()
        is_covered_call_assignment = (
            method == "exercida"
            and str(operation.get("Tipo", "")).upper() == "CALL"
            and str(operation.get("Estrategia", operation.get("Estratégia", ""))).lower() in {"venda coberta", "call coberta"}
        )
        is_short_put_assignment = (
            method == "exercida"
            and str(operation.get("Tipo", "")).upper() == "PUT"
            and str(operation.get("Estrategia", operation.get("Estratégia", ""))).lower() in {"venda", "wheel"}
        )
        if is_short_put_assignment:
            # No exercício da PUT vendida, strike menos prêmio recebido passa a
            # compor o custo das ações. O resultado será apurado na venda delas.
            bucket["exercise_deferred_count"] += 1
            continue
        if method == "exercida" and not is_covered_call_assignment:
            bucket["review_count"] += 1
            continue
        if method == "cancelada":
            continue
        result = _decimal(operation.get("Resultado_realizado"))
        irrf = _decimal(operation.get("IRRF"))
        # Resultado_realizado already has the registered IRRF deducted. For the
        # taxable result it is added back, then treated as a tax credit below.
        taxable_result = result + irrf
        is_day_trade = str(operation.get("Data_abertura", ""))[:10] == close_date[:10]
        result_key = "day_result" if is_day_trade else "common_result"
        irrf_key = "day_irrf" if is_day_trade else "common_irrf"
        bucket[result_key] += taxable_result
        bucket[irrf_key] += irrf
        bucket["tax_operation_candidates"].append({
            "option_code": str(operation.get("Ativo", "")),
            "underlying": str(operation.get("Ativo_subjacente", "")),
            "logo": str(operation.get("Logo_subjacente", "")),
            "open_date": str(operation.get("Data_abertura", ""))[:10],
            "close_date": close_date[:10],
            "modality": "Day trade" if is_day_trade else "Comum",
            "taxable_result": taxable_result,
        })

    first_month = min([*monthly.keys(), target_months[0]])
    month = first_month
    common_loss = day_loss = Decimal("0")
    common_irrf_credit = day_irrf_credit = Decimal("0")
    tax_carry = Decimal("0")
    calculated: dict[str, dict[str, Any]] = {}
    while month <= target_months[-1]:
        data = monthly.get(month, {})
        common_result = data.get("common_result", Decimal("0"))
        day_result = data.get("day_result", Decimal("0"))
        common_irrf_credit += data.get("common_irrf", Decimal("0"))
        day_irrf_credit += data.get("day_irrf", Decimal("0"))

        common_loss_used = min(common_loss, max(common_result, Decimal("0")))
        day_loss_used = min(day_loss, max(day_result, Decimal("0")))
        common_base = max(common_result - common_loss_used, Decimal("0"))
        day_base = max(day_result - day_loss_used, Decimal("0"))
        common_loss = common_loss - common_loss_used + max(-common_result, Decimal("0"))
        day_loss = day_loss - day_loss_used + max(-day_result, Decimal("0"))

        common_tax = common_base * Decimal("0.15")
        day_tax = day_base * Decimal("0.20")
        common_credit_used = min(common_tax, common_irrf_credit)
        day_credit_used = min(day_tax, day_irrf_credit)
        common_irrf_credit -= common_credit_used
        day_irrf_credit -= day_credit_used
        tax_calculated = max(common_tax + day_tax - common_credit_used - day_credit_used, Decimal("0"))
        tax_carried_in = tax_carry
        available_tax = tax_carried_in + tax_calculated
        estimated_darf = available_tax if available_tax >= Decimal("10") else Decimal("0")
        tax_carry = Decimal("0") if estimated_darf else available_tax
        tax_operations = []
        for modality, base, rate in (
            ("Comum", common_base, Decimal("0.15")),
            ("Day trade", day_base, Decimal("0.20")),
        ):
            candidates = [
                item for item in data.get("tax_operation_candidates", [])
                if item["modality"] == modality and item["taxable_result"] > 0
            ]
            positive_total = sum((item["taxable_result"] for item in candidates), Decimal("0"))
            allocated = Decimal("0")
            for index, item in enumerate(candidates):
                operation_base = (
                    base - allocated if index == len(candidates) - 1
                    else (base * item["taxable_result"] / positive_total).quantize(Decimal("0.01"))
                ) if positive_total else Decimal("0")
                allocated += operation_base
                if operation_base <= 0:
                    continue
                tax_operations.append({
                    "option_code": item["option_code"],
                    "underlying": item["underlying"],
                    "logo": item["logo"],
                    "open_date": item["open_date"],
                    "close_date": item["close_date"],
                    "modality": modality,
                    "taxable_base": str(operation_base),
                    "tax": str((operation_base * rate).quantize(Decimal("0.01"))),
                })
        calculated[month] = {
            "operations": data.get("operations", 0),
            "common_result": common_result,
            "day_result": day_result,
            "common_loss_compensated": common_loss_used,
            "day_loss_compensated": day_loss_used,
            "common_taxable_base": common_base,
            "day_taxable_base": day_base,
            "common_tax": common_tax,
            "day_tax": day_tax,
            "common_irrf_deducted": common_credit_used,
            "day_irrf_deducted": day_credit_used,
            "common_loss_carry": common_loss,
            "day_loss_carry": day_loss,
            "common_irrf_carry": common_irrf_credit,
            "day_irrf_carry": day_irrf_credit,
            "net_result": common_result + day_result,
            "loss_compensated": common_loss_used + day_loss_used,
            "taxable_base": common_base + day_base,
            "irrf_deducted": common_credit_used + day_credit_used,
            "tax_calculated": tax_calculated,
            "tax_carried_in": tax_carried_in,
            "estimated_darf": estimated_darf,
            "tax_carry": tax_carry,
            "loss_carry": common_loss + day_loss,
            "review_count": data.get("review_count", 0),
            "exercise_deferred_count": data.get("exercise_deferred_count", 0),
            "has_day_trade": bool(day_result or data.get("day_irrf", Decimal("0"))),
            "tax_operations": tax_operations,
        }
        month = _shift_month(month, 1)

    rows = []
    display_months = []
    month = first_month
    while month <= target_months[-1]:
        display_months.append(month)
        month = _shift_month(month, 1)
    for competence in display_months:
        if competence == current_month:
            relative_label = "Mês atual"
        elif competence == _shift_month(current_month, -1):
            relative_label = "Mês anterior"
        elif competence == _shift_month(current_month, 1):
            relative_label = "Mês seguinte"
        else:
            relative_label = "Histórico"
        row = {"competence": competence, "relative_label": relative_label, **calculated[competence]}
        if row["review_count"]:
            row["status"] = "Revisar exercício"
            row["status_class"] = "review"
        elif row["estimated_darf"] > 0:
            row["status"] = "DARF estimada"
            row["status_class"] = "due"
        elif row["tax_carry"] > 0:
            row["status"] = "Valor insuficiente para gerar DARF"
            row["status_class"] = "minimum"
        elif row["loss_carry"] > 0:
            row["status"] = "Prejuízo a compensar"
            row["status_class"] = "credit"
        else:
            row["status"] = "Sem DARF prevista"
            row["status_class"] = "clear"
        row["payment_month"] = _shift_month(competence, 1)
        rows.append(row)
    return {"rows": rows, "current_month": current_month, "revenue_code": "6015"}


def build_closed_dashboard(legacy, *, scope: str, selected_month: str) -> dict[str, Any]:
    operations, _closed_csv, _config = legacy.load_all()
    metadata = load_closure_metadata(legacy)
    all_closed = [serialize_closed_operation(legacy, operation, metadata.get(str(operation.get("ID")))) for operation in operations if str(operation.get("Status", "")).lower() == "encerrada"]
    today = date.today(); current_month = today.strftime("%Y-%m")
    month = selected_month if scope == "month" and selected_month else current_month
    def include(item):
        closed = item["Data_fechamento"][:7]
        if scope == "all": return True
        if scope == "year": return closed.startswith(str(today.year))
        return closed == month
    filtered = [item for item in all_closed if include(item)]
    accumulated = sum((_decimal(item["Resultado_realizado"]) for item in all_closed), Decimal("0"))
    month_profit = sum((_decimal(item["Resultado_realizado"]) for item in all_closed if item["Data_fechamento"][:7] == current_month), Decimal("0"))
    roi_average = sum((_decimal(item["ROI_realizado"]) for item in filtered), Decimal("0")) / Decimal(len(filtered)) if filtered else Decimal("0")
    months = sorted({item["Data_fechamento"][:7] for item in all_closed if item["Data_fechamento"]})
    groups = build_cycle_groups(filtered, result_key="Resultado_realizado", capital_key="Capital")
    return {"operations": filtered, "all_operations": all_closed, "groups": groups, "all_count": len(all_closed), "selected_count": len(filtered), "month_profit": month_profit, "accumulated_profit": accumulated, "roi_average": roi_average, "scope": scope, "selected_month": month, "available_months": months, "available_assets": sorted({item["Ativo_subjacente"] for item in all_closed if item.get("Ativo_subjacente")}), "darf_projection": build_darf_projection(all_closed)}


def build_asset_history(legacy, operations: list[dict[str, Any]], asset: str) -> dict[str, Any] | None:
    """Consolida todo o histórico encerrado e o preço médio líquido de um ativo."""
    ticker = str(asset or "").strip().upper()
    if not ticker:
        return None
    rows = [item for item in operations if str(item.get("Ativo_subjacente", "")).upper() == ticker]
    rows.sort(key=lambda item: (str(item.get("Data_fechamento", "")), str(item.get("Data_abertura", ""))), reverse=True)
    premium_total = Decimal("0")
    result_total = Decimal("0")
    capital_total = Decimal("0")
    for item in rows:
        strategy = str(item.get("Estrategia", "")).strip().lower()
        received = Decimal("0")
        if strategy not in {"compra"}:
            received = max(
                _decimal(item.get("Premio_bruto")) - _decimal(item.get("Custos")) - _decimal(item.get("IRRF")),
                Decimal("0"),
            )
        item["Premio_recebido_liquido"] = str(received)
        premium_total += received
        result_total += _decimal(item.get("Resultado_realizado"))
        capital_total += _decimal(item.get("Capital"))

    from services.equity_position_service import portfolio
    holding = next((item for item in portfolio(legacy) if str(item.get("asset", "")).upper() == ticker), None)
    adjusted_average = None
    if holding and int(holding.get("quantity", 0) or 0) > 0:
        adjusted_average = _decimal(
            holding.get("adjusted_average_price", holding.get("tax_cost_per_share"))
        )
    return {
        "asset": ticker,
        "operations": rows,
        "count": len(rows),
        "premium_total": premium_total,
        "result_total": result_total,
        "capital_total": capital_total,
        "roi_accumulated": result_total / capital_total * Decimal("100") if capital_total else Decimal("0"),
        "holding": holding,
        "adjusted_average": adjusted_average,
    }
