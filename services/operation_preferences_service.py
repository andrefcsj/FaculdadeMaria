"""Preferências operacionais que não alteram o registro financeiro original."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _path(legacy) -> Path:
    return Path(legacy.DATA) / "operation_preferences.json"


def normalize_exercise_interest(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "sim", "yes", "s"}


def normalize_underlying_asset(value: Any) -> str:
    ticker = str(value or "").strip().upper()
    return ticker if 5 <= len(ticker) <= 8 and ticker[-1:].isdigit() and ticker[:-1].isalnum() else ""


def _ensure_table(cursor) -> None:
    cursor.execute("""CREATE TABLE IF NOT EXISTS operation_preferences (
        operation_id TEXT PRIMARY KEY,
        exercise_interest BOOLEAN NOT NULL DEFAULT FALSE,
        underlying_asset TEXT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )""")
    cursor.execute("ALTER TABLE operation_preferences ADD COLUMN IF NOT EXISTS underlying_asset TEXT")


def load_operation_metadata(legacy) -> dict[str, dict[str, Any]]:
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            _ensure_table(cursor)
            connection.commit()
            cursor.execute("SELECT operation_id, exercise_interest, underlying_asset FROM operation_preferences")
            return {
                str(row[0]): {
                    "exercise_interest": bool(row[1]),
                    "underlying_asset": normalize_underlying_asset(row[2]),
                }
                for row in cursor.fetchall()
            }
        finally:
            connection.close()
    path = _path(legacy)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        metadata = {}
        for key, value in payload.items():
            record = value if isinstance(value, dict) else {"exercise_interest": value}
            metadata[str(key)] = {
                "exercise_interest": normalize_exercise_interest(record.get("exercise_interest", False)),
                "underlying_asset": normalize_underlying_asset(record.get("underlying_asset", "")),
            }
        return metadata
    except Exception:
        return {}


def load_operation_preferences(legacy) -> dict[str, bool]:
    return {key: value["exercise_interest"] for key, value in load_operation_metadata(legacy).items()}


def save_operation_metadata(legacy, operation_id: str, *, interested: Any, underlying_asset: Any = "") -> dict[str, Any]:
    value = normalize_exercise_interest(interested)
    underlying = normalize_underlying_asset(underlying_asset)
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            _ensure_table(cursor)
            cursor.execute("""INSERT INTO operation_preferences(operation_id, exercise_interest, underlying_asset)
                VALUES (%s, %s, %s) ON CONFLICT(operation_id) DO UPDATE SET
                exercise_interest=EXCLUDED.exercise_interest,
                underlying_asset=COALESCE(NULLIF(EXCLUDED.underlying_asset, ''), operation_preferences.underlying_asset),
                updated_at=NOW()""", (str(operation_id), value, underlying or None))
            connection.commit()
        finally:
            connection.close()
    else:
        rows = load_operation_metadata(legacy)
        previous = rows.get(str(operation_id), {})
        rows[str(operation_id)] = {
            "exercise_interest": value,
            "underlying_asset": underlying or previous.get("underlying_asset", ""),
        }
        path = _path(legacy)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    return {"exercise_interest": value, "underlying_asset": underlying}


def save_exercise_interest(legacy, operation_id: str, interested: Any) -> bool:
    value = normalize_exercise_interest(interested)
    save_operation_metadata(legacy, operation_id, interested=value)
    return value


def delete_operation_preference(legacy, operation_id: str) -> None:
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM operation_preferences WHERE operation_id=%s", (str(operation_id),))
            connection.commit()
            return
        finally:
            connection.close()
    rows = load_operation_metadata(legacy)
    rows.pop(str(operation_id), None)
    path = _path(legacy)
    if path.exists():
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_operation_preferences(operations: list[dict[str, Any]], legacy) -> list[dict[str, Any]]:
    preferences = load_operation_metadata(legacy)
    for operation in operations:
        metadata = preferences.get(str(operation.get("ID", "")), {})
        operation["Interesse_exercicio"] = metadata.get("exercise_interest", False)
        underlying = normalize_underlying_asset(metadata.get("underlying_asset", ""))
        if underlying:
            operation["Ativo_subjacente"] = underlying
    return operations


def operation_underlying(legacy, operation: dict[str, Any]) -> str:
    saved = normalize_underlying_asset(operation.get("Ativo_subjacente", ""))
    return saved or legacy.infer_acao_from_option(str(operation.get("Ativo", "")))
