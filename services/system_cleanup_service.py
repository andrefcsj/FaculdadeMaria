"""Limpeza operacional com escopo explícito e preservação de configurações."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from services.brokerage_note_service import load_imported_notes
from services.closed_operations_service import load_closure_metadata


@dataclass(frozen=True)
class CleanupPreview:
    operation_ids: tuple[str, ...]
    operations: int
    imported_notes: int
    closures: int
    legacy_closed: int

    @property
    def total(self) -> int:
        return self.operations + self.imported_notes + self.closures + self.legacy_closed


def _matches(value: Any, scope: str, period: str, parse_date) -> bool:
    parsed = parse_date(str(value or ""))
    if not parsed:
        return scope == "all"
    if scope == "month":
        return parsed.strftime("%Y-%m") == period
    if scope == "year":
        return str(parsed.year) == period
    return scope == "all"


def _legacy_month_matches(value: str, scope: str, period: str) -> bool:
    text = str(value or "").strip()
    if scope == "all":
        return True
    months = {"Jan":1,"Fev":2,"Mar":3,"Abr":4,"Mai":5,"Jun":6,"Jul":7,"Ago":8,"Set":9,"Out":10,"Nov":11,"Dez":12}
    try:
        label, short_year = text.split("/")
        year = 2000 + int(short_year)
        month = months[label[:3].title()]
    except Exception:
        return False
    return str(year) == period if scope == "year" else f"{year:04d}-{month:02d}" == period


def _legacy_closed_rows(legacy) -> list[dict[str, str]]:
    return legacy.read_csv(legacy.FECHADAS)


def preview_cleanup(legacy, *, scope: str, period: str) -> CleanupPreview:
    operations = legacy.read_operacoes()
    ids = tuple(str(row.get("ID")) for row in operations if _matches(row.get("Data abertura"), scope, period, legacy.parse_date))
    id_set = set(ids)
    notes = load_imported_notes(legacy)
    closures = load_closure_metadata(legacy)
    legacy_closed = _legacy_closed_rows(legacy)
    return CleanupPreview(
        operation_ids=ids,
        operations=len(ids),
        imported_notes=sum(1 for row in notes if scope == "all" or str(row.get("operation_id")) in id_set),
        closures=sum(1 for key in closures if scope == "all" or key in id_set),
        legacy_closed=sum(1 for row in legacy_closed if _legacy_month_matches(row.get("Mes", ""), scope, period)),
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def execute_cleanup(legacy, *, scope: str, period: str) -> CleanupPreview:
    preview = preview_cleanup(legacy, scope=scope, period=period)
    ids = set(preview.operation_ids)
    if legacy.USE_POSTGRES:
        # Garante que as tabelas auxiliares existam antes da transação destrutiva.
        load_imported_notes(legacy); load_closure_metadata(legacy)
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            if scope == "all":
                cur.execute("DELETE FROM brokerage_notes")
                cur.execute("DELETE FROM operation_closure_metadata")
                cur.execute("DELETE FROM operacoes")
            elif ids:
                values = list(ids)
                cur.execute("DELETE FROM brokerage_notes WHERE payload->>'operation_id' = ANY(%s)", (values,))
                cur.execute("DELETE FROM operation_closure_metadata WHERE operation_id = ANY(%s)", (values,))
                cur.execute("DELETE FROM operacoes WHERE id::text = ANY(%s)", (values,))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        operations = legacy.read_csv(legacy.OPERACOES)
        legacy.write_csv(legacy.OPERACOES, [row for row in operations if str(row.get("ID")) not in ids], ["ID","Data abertura","Ativo","Tipo","Estratégia","Status","Contratos","Strike","Premio_opcao","Custos","IRRF","Vencimento","Cotacao_atual","Resultado_realizado"])
        notes = load_imported_notes(legacy)
        kept_notes = [] if scope == "all" else [row for row in notes if str(row.get("operation_id")) not in ids]
        _write_json(legacy.DATA / "brokerage_notes.json", kept_notes)
        closures = load_closure_metadata(legacy)
        kept_closures = {} if scope == "all" else {key: row for key, row in closures.items() if key not in ids}
        _write_json(legacy.DATA / "operation_closures.json", kept_closures)
    legacy_rows = _legacy_closed_rows(legacy)
    legacy.write_csv(legacy.FECHADAS, [row for row in legacy_rows if not _legacy_month_matches(row.get("Mes", ""), scope, period)], list(legacy_rows[0].keys()) if legacy_rows else ["Mes"])
    return preview


def expected_confirmation(scope: str, period: str) -> str:
    if scope == "month":
        return f"APAGAR {period}"
    if scope == "year":
        return f"APAGAR {period}"
    return "ZERAR FACULDADEMARIA"
