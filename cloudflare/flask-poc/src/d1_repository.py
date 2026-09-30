"""Acesso mínimo ao D1 a partir de handlers Flask síncronos (WSGI)."""

from __future__ import annotations

import json
from typing import Any

from flask import request
from pyodide.ffi import run_sync


def _run(sql: str, *params: object):
    statement = request.environ["workers.env"].DB.prepare(sql)
    if params:
        statement = statement.bind(*params)
    return run_sync(statement.run())


def _rows(result: Any) -> list[dict[str, Any]]:
    """Converte os objetos do runtime JavaScript em dicionários Python."""
    return [dict(row) for row in result.results]


def list_operations() -> list[dict[str, Any]]:
    result = _run(
        """
        SELECT id, data_abertura, ativo, tipo, estrategia, status, contratos,
               strike, premio_opcao, custos, irrf, vencimento, cotacao_atual,
               resultado_realizado
        FROM operacoes
        ORDER BY id
        """
    )
    return _rows(result)


def list_config() -> list[dict[str, Any]]:
    return _rows(_run("SELECT parametro, valor FROM config ORDER BY parametro"))


def list_closed_operations() -> list[dict[str, Any]]:
    rows = _rows(
        _run(
            "SELECT closed_id, payload, closed_at FROM closed_operations "
            "ORDER BY closed_at DESC, closed_id"
        )
    )
    return [
        {"closed_id": row["closed_id"], "closed_at": row["closed_at"], **json.loads(row["payload"])}
        for row in rows
    ]
