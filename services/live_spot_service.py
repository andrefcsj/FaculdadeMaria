"""Atualiza cotações dos ativos subjacentes sem alterar o registro financeiro."""
from __future__ import annotations

from typing import Any, Sequence
from concurrent.futures import ThreadPoolExecutor
import math

from services.operation_preferences_service import operation_underlying
from services.sldx_market_service import fetch_stock_price, SldxMarketError


def with_current_underlying_quotes(legacy, operations: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retorna cópias das operações usando a cotação atual quando disponível.

    Não reutiliza a cotação de cadastro para emitir alertas de exercício.
    Falhas ficam sem cotação, em vez de apresentar um cenário antigo como atual.
    """
    enriched = [dict(operation) for operation in operations]
    tickers = sorted({
        operation_underlying(legacy, operation)
        for operation in enriched
        if str(operation.get("Status", "")).lower() == "aberta"
    } - {""})
    if not tickers:
        return enriched
    def quote(ticker):
        try:
            price = float(fetch_stock_price(ticker))
            return ticker, price if math.isfinite(price) and price > 0 else None
        except (SldxMarketError, ValueError, TypeError):
            return ticker, None
    with ThreadPoolExecutor(max_workers=min(6, len(tickers))) as pool:
        prices = dict(pool.map(quote, tickers))
    for operation in enriched:
        ticker = operation_underlying(legacy, operation)
        price = prices.get(ticker)
        if str(operation.get("Status", "")).lower() != "aberta":
            continue
        operation["Cotacao_n"] = price
        operation["Cotacao_atual"] = price
        operation["Cotacao_fonte"] = "SLDX API — última consulta" if price else "Cotação indisponível"
    return enriched
