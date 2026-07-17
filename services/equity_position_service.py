"""Carteira de ações originada por exercício e cobertura de CALLs."""
from __future__ import annotations

import json
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


_LOTS_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _cache_key(legacy) -> str:
    return str(getattr(legacy, "DATABASE_URL", "") or getattr(legacy, "DATA", "default"))


def _invalidate_cache(legacy) -> None:
    _LOTS_CACHE.pop(_cache_key(legacy), None)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except Exception:
        return Decimal("0")


def _path(legacy) -> Path:
    return legacy.DATA / "equity_lots.json"


def load_equity_lots(legacy) -> list[dict[str, Any]]:
    if getattr(legacy, "USE_POSTGRES", False):
        cached = _LOTS_CACHE.get(_cache_key(legacy))
        if cached and time.time() - cached[0] < 30:
            return [dict(item) for item in cached[1]]
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS equity_lots (
                lot_id TEXT PRIMARY KEY, payload JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            conn.commit()
            cur.execute("SELECT payload FROM equity_lots ORDER BY created_at")
            values = [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in cur.fetchall()]
            _LOTS_CACHE[_cache_key(legacy)] = (time.time(), values)
            return [dict(item) for item in values]
        finally:
            conn.close()
    path = _path(legacy)
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []
    except Exception:
        return []


def save_equity_lot(legacy, lot: dict[str, Any]) -> bool:
    lot_id = str(lot.get("lot_id", "")).strip()
    if not lot_id:
        raise ValueError("Lote de ações sem identificador.")
    record = {**lot, "lot_id": lot_id, "updated_at": datetime.now().isoformat(timespec="seconds")}
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS equity_lots (
                lot_id TEXT PRIMARY KEY, payload JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cur.execute(
                "INSERT INTO equity_lots (lot_id,payload) VALUES (%s,%s::jsonb) ON CONFLICT (lot_id) DO NOTHING",
                (lot_id, json.dumps(record, ensure_ascii=False)),
            )
            inserted = cur.rowcount > 0
            conn.commit()
            _invalidate_cache(legacy)
            return inserted
        finally:
            conn.close()
    lots = load_equity_lots(legacy)
    if any(str(item.get("lot_id")) == lot_id for item in lots):
        return False
    lots.append(record)
    path = _path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lots, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def create_put_assignment_lot(legacy, operation: dict[str, Any], note_payload: dict[str, Any]) -> dict[str, Any]:
    trade = note_payload.get("trade", {})
    quantity = int(trade.get("quantity") or 0)
    strike = _decimal(trade.get("unit_price") or operation.get("Strike"))
    exercise_costs = _decimal(trade.get("allocated_costs")) + _decimal(trade.get("allocated_irrf"))
    contracts = _decimal(operation.get("Contratos"))
    contract_size = _decimal(legacy.load_config().get("Tamanho contrato opcoes", 100))
    premium_gross = _decimal(operation.get("Premio_opcao")) * contracts * contract_size
    option_costs = _decimal(operation.get("Custos")) + _decimal(operation.get("IRRF"))
    exercise_total = strike * Decimal(quantity)
    underlying = str(operation.get("Ativo_subjacente") or legacy.infer_acao_from_option(str(operation.get("Ativo", "")))).upper()
    return {
        "lot_id": f"exercise:{operation.get('ID')}",
        "asset": underlying,
        "quantity": quantity,
        "available_quantity": quantity,
        "acquisition_date": str(note_payload.get("trade_date", "")),
        "exercise_price": str(strike),
        "exercise_total": str(exercise_total),
        "exercise_costs": str(exercise_costs),
        "cash_cost_total": str(exercise_total + exercise_costs),
        # Regra fiscal do lançador de PUT: strike menos prêmio recebido.
        "option_premium_gross": str(premium_gross),
        "option_opening_costs": str(option_costs),
        "tax_cost_total": str(exercise_total + exercise_costs - premium_gross),
        "tax_cost_per_share": str((exercise_total + exercise_costs - premium_gross) / Decimal(quantity)) if quantity else "0",
        "source": "Exercício de PUT vendida",
        "source_operation_id": str(operation.get("ID", "")),
        "source_option": str(operation.get("Ativo", "")).upper(),
        "source_note_key": f"{note_payload.get('document_hash')}:{int(trade.get('trade_index', 0))}",
    }


def portfolio(legacy, operations: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    operations = operations if operations is not None else legacy.read_operacoes()
    if operations and not all("Interesse_exercicio" in operation for operation in operations):
        from services.operation_preferences_service import apply_operation_preferences
        operations = apply_operation_preferences(operations, legacy)
    grouped: dict[str, dict[str, Any]] = {}
    for lot in load_equity_lots(legacy):
        asset = str(lot.get("asset", "")).upper()
        if not asset:
            continue
        item = grouped.setdefault(asset, {"asset": asset, "quantity": 0, "cash_cost_total": Decimal("0"), "tax_cost_total": Decimal("0"), "sources": []})
        item["quantity"] += int(lot.get("available_quantity", lot.get("quantity", 0)) or 0)
        item["cash_cost_total"] += _decimal(lot.get("cash_cost_total"))
        item["tax_cost_total"] += _decimal(lot.get("tax_cost_total"))
        item["sources"].append(lot)
    size = int(legacy.load_config().get("Tamanho contrato opcoes", 100))
    for item in grouped.values():
        covered = sum(
            int(_decimal(op.get("Contratos")) * size)
            for op in operations
            if str(op.get("Status", "")).lower() == "aberta"
            and str(op.get("Tipo", "")).upper() == "CALL"
            and str(op.get("Estratégia", "")).lower() in {"venda coberta", "call coberta"}
            and str(op.get("Ativo_subjacente") or legacy.infer_acao_from_option(str(op.get("Ativo", "")))).upper() == item["asset"]
        )
        item["covered_quantity"] = covered
        item["available_quantity"] = max(item["quantity"] - covered, 0)
        item["cash_cost_per_share"] = item["cash_cost_total"] / item["quantity"] if item["quantity"] else Decimal("0")
        item["tax_cost_per_share"] = item["tax_cost_total"] / item["quantity"] if item["quantity"] else Decimal("0")
        for key in ("cash_cost_total", "tax_cost_total", "cash_cost_per_share", "tax_cost_per_share"):
            item[key] = float(item[key])
    return sorted(grouped.values(), key=lambda value: value["asset"])


def available_coverage(legacy, asset: str, operations=None, *, exclude_operation_id: str | None = None) -> int:
    rows = operations if operations is not None else legacy.read_operacoes()
    if exclude_operation_id is not None:
        rows = [row for row in rows if str(row.get("ID")) != str(exclude_operation_id)]
    match = next((item for item in portfolio(legacy, rows) if item["asset"] == str(asset).upper()), None)
    return int(match["available_quantity"]) if match else 0


def validate_covered_call(legacy, asset: str, contracts: Decimal, operations=None, *, exclude_operation_id: str | None = None) -> int:
    required = int(contracts * _decimal(legacy.load_config().get("Tamanho contrato opcoes", 100)))
    available = available_coverage(legacy, asset, operations, exclude_operation_id=exclude_operation_id)
    if required > available:
        raise ValueError(f"Cobertura insuficiente: {required} ações necessárias e {available} disponíveis.")
    return available - required


def exercise_covered_call(legacy, operation: dict[str, Any]) -> Decimal:
    """Baixa ações em FIFO e devolve o ganho fiscal estimado da entrega."""
    quantity = int(_decimal(operation.get("Contratos")) * _decimal(legacy.load_config().get("Tamanho contrato opcoes", 100)))
    remaining = quantity
    lots = load_equity_lots(legacy)
    consumed_cost = Decimal("0")
    changed = []
    asset = str(operation.get("Ativo_subjacente") or legacy.infer_acao_from_option(str(operation.get("Ativo", "")))).upper()
    for lot in lots:
        if remaining <= 0 or str(lot.get("asset", "")).upper() != asset:
            continue
        available = int(lot.get("available_quantity", lot.get("quantity", 0)) or 0)
        take = min(available, remaining)
        if not take:
            continue
        unit_tax_cost = _decimal(lot.get("tax_cost_per_share"))
        consumed_cost += unit_tax_cost * take
        lot["available_quantity"] = available - take
        remaining -= take
        changed.append(lot)
    if remaining:
        raise ValueError(f"Faltam {remaining} ações para liquidar o exercício desta CALL coberta.")
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            for lot in changed:
                cur.execute("UPDATE equity_lots SET payload=%s::jsonb WHERE lot_id=%s", (json.dumps(lot, ensure_ascii=False), lot["lot_id"]))
            conn.commit()
            _invalidate_cache(legacy)
        finally:
            conn.close()
    else:
        _path(legacy).write_text(json.dumps(lots, ensure_ascii=False, indent=2), encoding="utf-8")
    proceeds = _decimal(operation.get("Strike")) * quantity
    premium_net = _decimal(operation.get("Premio_opcao")) * quantity - _decimal(operation.get("Custos")) - _decimal(operation.get("IRRF"))
    return proceeds + premium_net - consumed_cost
