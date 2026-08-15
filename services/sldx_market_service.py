"""Cliente mínimo e seguro para cotações de ações na SLDX API."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation

from engine import OptionOpportunity


class SldxMarketError(RuntimeError):
    """Falha ao consultar ou interpretar uma resposta da SLDX."""


@dataclass(frozen=True, slots=True)
class SldxOptionsResult:
    opportunities: tuple[OptionOpportunity, ...]
    successful_tickers: tuple[str, ...]
    failures: dict[str, str]


def _credentials(token: str | None, base_url: str | None) -> tuple[str, str]:
    api_token = (token if token is not None else os.getenv("SLDX_API_TOKEN", "")).strip()
    if not api_token:
        raise SldxMarketError("SLDX_API_TOKEN não configurado.")
    api_base = (base_url if base_url is not None else os.getenv(
        "SLDX_API_BASE_URL", "https://api.sldx.com.br"
    )).strip().rstrip("/")
    return api_token, api_base


def _request_json(path: str, *, token: str, base_url: str, timeout: float) -> dict:
    request = urllib.request.Request(
        f"{base_url}{path}",
        headers={
            "Accept": "application/json", "Authorization": f"Bearer {token}",
            "User-Agent": "FaculdadeMaria/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SldxMarketError(f"SLDX respondeu HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SldxMarketError("SLDX temporariamente indisponível.") from exc
    if not isinstance(payload, dict) or payload.get("success") is False:
        raise SldxMarketError("SLDX recusou a requisição.")
    return payload


def _decimal(value, *, positive: bool = False) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if parsed < 0 or (positive and parsed <= 0):
        return None
    return parsed


def fetch_option_chain(
    ticker: str, *, token: str | None = None, base_url: str | None = None,
    timeout: float = 12,
) -> tuple[OptionOpportunity, ...]:
    """Busca e normaliza as PUTs de um ativo para o Decision Engine."""
    symbol = str(ticker or "").upper().strip().removesuffix(".SA")
    if not symbol:
        raise SldxMarketError("Ticker não informado.")
    api_token, api_base = _credentials(token, base_url)
    encoded = urllib.parse.quote(symbol, safe="")
    chain = _request_json(
        f"/stock-options-chain/{encoded}", token=api_token,
        base_url=api_base, timeout=timeout,
    )
    summary = _request_json(
        f"/stock-options/{encoded}", token=api_token,
        base_url=api_base, timeout=timeout,
    )
    result = chain.get("result") if isinstance(chain.get("result"), dict) else {}
    spot = _decimal(result.get("underlying_price"), positive=True)
    options = result.get("options") if isinstance(result.get("options"), list) else []
    if not spot or not options:
        raise SldxMarketError(f"SLDX não retornou cadeia válida para {symbol}.")
    try:
        trade_date = date.fromisoformat(str(summary.get("trade_date")))
    except ValueError:
        trade_date = date.today()
    timestamp = datetime.combine(trade_date, time.min, tzinfo=timezone.utc)
    opportunities = []
    for row in options:
        if not isinstance(row, dict) or str(row.get("type", "")).upper() != "PUT":
            continue
        try:
            expiry = date.fromisoformat(str(row.get("expiration_date")))
        except ValueError:
            continue
        strike = _decimal(row.get("strike"), positive=True)
        premium = _decimal(row.get("last_price"))
        if expiry < date.today() or strike is None or premium is None:
            continue
        bid = _decimal(row.get("bid"), positive=True)
        ask = _decimal(row.get("ask"), positive=True)
        if bid is not None and ask is not None and ask < bid:
            bid = ask = None
        raw_volume = _decimal(row.get("volume"))
        raw_iv = _decimal(row.get("implied_volatility"))
        opportunities.append(OptionOpportunity(
            asset=symbol, option_code=str(row.get("symbol", "")).upper(), option_type="PUT",
            expiry=expiry, spot_price=spot, strike=strike, premium=premium,
            bid=bid, ask=ask, volume=int(raw_volume) if raw_volume is not None else None,
            liquidity=raw_volume, implied_volatility=(raw_iv / Decimal("100") if raw_iv is not None else None),
            timestamp=timestamp, source="sldx_api", data_confidence=Decimal("0.95"),
        ))
    if not opportunities:
        raise SldxMarketError(f"SLDX não retornou PUT válida para {symbol}.")
    return tuple(opportunities)


def fetch_options_market(
    tickers, *, token: str | None = None, base_url: str | None = None,
    timeout: float = 12, max_workers: int = 5,
) -> SldxOptionsResult:
    """Atualiza vários ativos em paralelo, isolando falhas por ticker."""
    symbols = tuple(dict.fromkeys(str(item).upper().strip() for item in tickers if str(item).strip()))
    opportunities: list[OptionOpportunity] = []
    successful: list[str] = []
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, max(len(symbols), 1))) as executor:
        futures = {
            executor.submit(fetch_option_chain, symbol, token=token, base_url=base_url, timeout=timeout): symbol
            for symbol in symbols
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                opportunities.extend(future.result())
                successful.append(symbol)
            except SldxMarketError as exc:
                failures[symbol] = str(exc)
    return SldxOptionsResult(
        opportunities=tuple(opportunities), successful_tickers=tuple(sorted(successful)),
        failures=failures,
    )


def fetch_stock_price(
    ticker: str,
    *,
    token: str | None = None,
    base_url: str | None = None,
    timeout: float = 4,
) -> float:
    """Retorna o preço atual de um ticker brasileiro.

    O token simples da SLDX tem o formato ``KID.SECRET`` e nunca é incluído
    em mensagens de erro para evitar vazamento acidental em logs.
    """
    symbol = str(ticker or "").upper().strip().removesuffix(".SA")
    if not symbol:
        raise SldxMarketError("Ticker não informado.")

    api_token, api_base = _credentials(token, base_url)
    payload = _request_json(
        f"/stock-price/{urllib.parse.quote(symbol, safe='')}", token=api_token,
        base_url=api_base, timeout=timeout,
    )
    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    quote = {}
    if isinstance(result, dict):
        quote = result.get(symbol) or result.get(symbol.lower()) or {}
    price = quote.get("current_price") if isinstance(quote, dict) else None
    try:
        value = float(price)
    except (TypeError, ValueError) as exc:
        raise SldxMarketError("SLDX retornou uma cotação inválida.") from exc
    if value <= 0:
        raise SldxMarketError("SLDX retornou uma cotação inválida.")
    return value
