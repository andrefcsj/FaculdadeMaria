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


def load_operation_preferences(legacy) -> dict[str, bool]:
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS operation_preferences (
                operation_id TEXT PRIMARY KEY,
                exercise_interest BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            connection.commit()
            cursor.execute("SELECT operation_id, exercise_interest FROM operation_preferences")
            return {str(row[0]): bool(row[1]) for row in cursor.fetchall()}
        finally:
            connection.close()
    path = _path(legacy)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(key): normalize_exercise_interest(value) for key, value in payload.items()} if isinstance(payload, dict) else {}
    except Exception:
        return {}


def save_exercise_interest(legacy, operation_id: str, interested: Any) -> bool:
    value = normalize_exercise_interest(interested)
    if getattr(legacy, "USE_POSTGRES", False):
        connection = legacy.get_pg_conn()
        try:
            cursor = connection.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS operation_preferences (
                operation_id TEXT PRIMARY KEY,
                exercise_interest BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cursor.execute("""INSERT INTO operation_preferences(operation_id, exercise_interest)
                VALUES (%s, %s) ON CONFLICT(operation_id) DO UPDATE SET
                exercise_interest=EXCLUDED.exercise_interest, updated_at=NOW()""", (str(operation_id), value))
            connection.commit()
            return value
        finally:
            connection.close()
    rows = load_operation_preferences(legacy)
    rows[str(operation_id)] = value
    path = _path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
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
    rows = load_operation_preferences(legacy)
    rows.pop(str(operation_id), None)
    path = _path(legacy)
    if path.exists():
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def apply_operation_preferences(operations: list[dict[str, Any]], legacy) -> list[dict[str, Any]]:
    preferences = load_operation_preferences(legacy)
    for operation in operations:
        operation["Interesse_exercicio"] = preferences.get(str(operation.get("ID", "")), False)
    return operations
