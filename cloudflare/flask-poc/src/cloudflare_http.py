"""Ponte HTTP síncrona para handlers Flask executados em Python Workers."""

from __future__ import annotations

from typing import Mapping

from js import fetch
from pyodide.ffi import run_sync


def get_status(url: str, headers: Mapping[str, str] | None = None) -> int:
    # ``fetch`` recebe um RequestInit JavaScript; um ``dict`` Python não é
    # convertido automaticamente nesse runtime. Para a prova de conectividade
    # não são necessários cabeçalhos.
    del headers
    response = run_sync(fetch(url))
    return int(response.status)
