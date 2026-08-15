"""Cliente mínimo e seguro para cotações de ações na SLDX API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class SldxMarketError(RuntimeError):
    """Falha ao consultar ou interpretar uma resposta da SLDX."""


def fetch_stock_price(ticker: str, *, token: str | None = None,
                      base_url: str | None = None, timeout: float = 4) -> float:
    """Retorna o preço atual sem incluir credenciais em mensagens de erro."""
    symbol = str(ticker or "").upper().strip().removesuffix(".SA")
    if not symbol:
        raise SldxMarketError("Ticker não informado.")
    api_token = (token if token is not None else os.getenv("SLDX_API_TOKEN", "")).strip()
    if not api_token:
        raise SldxMarketError("SLDX_API_TOKEN não configurado.")
    api_base = (base_url if base_url is not None else os.getenv(
        "SLDX_API_BASE_URL", "https://api.sldx.com.br"
    )).strip().rstrip("/")
    url = f"{api_base}/stock-price/{urllib.parse.quote(symbol, safe='')}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Authorization": f"Bearer {api_token}",
        "User-Agent": "FaculdadeMaria/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SldxMarketError(f"SLDX respondeu HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SldxMarketError("SLDX temporariamente indisponível.") from exc
    if isinstance(payload, dict) and payload.get("success") is False:
        raise SldxMarketError("SLDX recusou a requisição.")
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    quote = result.get(symbol) or result.get(symbol.lower()) or {} if isinstance(result, dict) else {}
    try:
        value = float(quote.get("current_price"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise SldxMarketError("SLDX retornou uma cotação inválida.") from exc
    if value <= 0:
        raise SldxMarketError("SLDX retornou uma cotação inválida.")
    return value
