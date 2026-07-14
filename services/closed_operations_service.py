"""Persistência de encerramento e visão executiva de operações fechadas."""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


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
            cur = conn.cursor(); cur.execute("DELETE FROM operacoes WHERE id=%s", (str(operation_id),)); conn.commit(); return
        finally:
            conn.close()
    remaining = [row for row in rows if str(row.get("ID")) != str(operation_id)]
    legacy.write_csv(legacy.OPERACOES, remaining, FIELDS)


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
    roi = result / capital * Decimal("100") if capital else Decimal("0")
    close_date = metadata.get("close_date") or operation.get("Data fechamento") or ""
    underlying = legacy.infer_acao_from_option(operation.get("Ativo", ""))
    underlying_logo = (
        f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{underlying}.png"
        if underlying else ""
    )
    return {
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
    return {"operations": filtered, "all_count": len(all_closed), "selected_count": len(filtered), "month_profit": month_profit, "accumulated_profit": accumulated, "roi_average": roi_average, "scope": scope, "selected_month": month, "available_months": months}
