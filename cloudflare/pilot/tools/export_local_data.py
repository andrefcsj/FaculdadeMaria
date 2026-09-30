#!/usr/bin/env python3
"""Gera SQL D1 auditável a partir do armazenamento local do FaculdadeMaria.

Não conecta a banco remoto, não lê .env e não executa o SQL gerado. O arquivo
de saída deve ser revisado antes de ser aplicado ao banco-piloto via Wrangler.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


OPERATION_COLUMNS = (
    "data_abertura", "ativo", "tipo", "estrategia", "status", "contratos",
    "strike", "premio_opcao", "custos", "irrf", "vencimento",
    "cotacao_atual", "resultado_realizado",
)
OPERATION_CSV_COLUMNS = (
    "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos",
    "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento",
    "Cotacao_atual", "Resultado_realizado",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _sql_text(value: object) -> str:
    if value is None:
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def _closed_id(row: dict[str, str], index: int) -> str:
    canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{index}:{canonical}".encode("utf-8")).hexdigest()[:20]
    return f"closed-{digest}"


def build_sql(data_dir: Path) -> str:
    operations = _read_csv(data_dir / "operacoes.csv")
    config = _read_csv(data_dir / "config.csv")
    closed = _read_csv(data_dir / "fechadas.csv")
    statements = [
        "-- Gerado localmente por export_local_data.py; revisar antes de aplicar.",
        "BEGIN TRANSACTION;",
    ]

    for row in operations:
        values = [_sql_text(row.get(column, "")) for column in OPERATION_CSV_COLUMNS]
        statements.append(
            "INSERT INTO operacoes (" + ", ".join(OPERATION_COLUMNS) + ") VALUES ("
            + ", ".join(values) + ");"
        )

    for row in config:
        parameter = row.get("Parametro", "").strip()
        if parameter:
            statements.append(
                "INSERT INTO config (parametro, valor) VALUES ("
                f"{_sql_text(parameter)}, {_sql_text(row.get('Valor', ''))}"
                ") ON CONFLICT(parametro) DO UPDATE SET valor = excluded.valor;"
            )

    for index, row in enumerate(closed, start=1):
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        closed_at = row.get("Data fechamento") or row.get("Data Fechamento") or ""
        statements.append(
            "INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES ("
            f"{_sql_text(_closed_id(row, index))}, {_sql_text(payload)}, {_sql_text(closed_at)}"
            ") ON CONFLICT(closed_id) DO UPDATE SET payload = excluded.payload, "
            "closed_at = excluded.closed_at;"
        )

    statements.extend(["COMMIT;", ""])
    return "\n".join(statements)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_sql(args.data_dir), encoding="utf-8")
    print(f"SQL de importação criado: {args.output}")


if __name__ == "__main__":
    main()
