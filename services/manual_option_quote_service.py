"""Cotações de opções informadas manualmente pelo usuário no ProfitPro."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _path(legacy) -> Path:
    return Path(legacy.DATA) / "manual_option_quotes.json"


def _price(value: Any) -> Decimal:
    text = str(value or "").strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        parsed = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Preço atual inválido.") from exc
    if parsed < 0:
        raise ValueError("Preço atual não pode ser negativo.")
    return parsed


def _quoted_at(value: Any) -> str:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text) if text else datetime.now()
    except ValueError as exc:
        raise ValueError("Data e horário da cotação inválidos.") from exc
    return parsed.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def _ensure_table(cursor) -> None:
    cursor.execute("""CREATE TABLE IF NOT EXISTS manual_option_quotes (
        option_code TEXT PRIMARY KEY,
        price NUMERIC NOT NULL,
        quoted_at TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""")


def load_manual_option_quotes(legacy) -> dict[str, dict[str, str]]:
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            _ensure_table(cursor)
            connection.commit()
            cursor.execute("SELECT option_code, price, quoted_at FROM manual_option_quotes")
            return {str(row[0]).upper(): {"price": str(row[1]), "quoted_at": str(row[2])} for row in cursor.fetchall()}
        finally:
            connection.close()
    path = _path(legacy)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def save_manual_option_quote(legacy, option_code: Any, price: Any, quoted_at: Any) -> dict[str, str]:
    code = str(option_code or "").strip().upper()
    if not code:
        raise ValueError("Código da opção é obrigatório.")
    record = {"price": str(_price(price)), "quoted_at": _quoted_at(quoted_at)}
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            _ensure_table(cursor)
            cursor.execute("""INSERT INTO manual_option_quotes(option_code, price, quoted_at)
                VALUES (%s, %s, %s) ON CONFLICT(option_code) DO UPDATE SET
                price=EXCLUDED.price, quoted_at=EXCLUDED.quoted_at, updated_at=NOW()""",
                (code, record["price"], record["quoted_at"]))
            connection.commit()
        finally:
            connection.close()
    else:
        rows = load_manual_option_quotes(legacy)
        rows[code] = record
        path = _path(legacy)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    return record


def format_quote_source(record: dict[str, Any]) -> str:
    try:
        moment = datetime.fromisoformat(str(record.get("quoted_at", "")))
        return f"ProfitPro • {moment.strftime('%d/%m/%Y às %H:%M')}"
    except ValueError:
        return "ProfitPro • horário não informado"
