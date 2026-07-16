"""Atualiza cotações dos ativos subjacentes sem alterar o registro financeiro."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, Sequence


def with_current_underlying_quotes(legacy, operations: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retorna cópias das operações usando a cotação atual quando disponível.

    Se a fonte estiver indisponível, preserva a última cotação registrada para que
    o Dashboard continue funcional e deixe claro que não inventou um valor.
    """
    enriched = [dict(operation) for operation in operations]
    tickers = sorted({
        legacy.infer_acao_from_option(str(operation.get("Ativo", "")))
        for operation in enriched
        if str(operation.get("Status", "")).lower() == "aberta"
    } - {""})
    if not tickers:
        return enriched
    with ThreadPoolExecutor(max_workers=min(6, len(tickers))) as executor:
        prices = dict(zip(tickers, executor.map(legacy.cotacao_yahoo, tickers)))
    for operation in enriched:
        ticker = legacy.infer_acao_from_option(str(operation.get("Ativo", "")))
        price = prices.get(ticker)
        if price is not None and float(price) > 0:
            operation["Cotacao_n"] = float(price)
            operation["Cotacao_atual"] = float(price)
            operation["Cotacao_fonte"] = "Yahoo Finance intradiário"
    return enriched
