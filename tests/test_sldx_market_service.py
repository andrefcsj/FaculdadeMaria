import json
from decimal import Decimal
from io import BytesIO

import pytest

from services.sldx_market_service import (
    SldxMarketError, fetch_option_chain, fetch_options_market, fetch_stock_price,
)


class FakeResponse:
    def __init__(self, payload):
        self.body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body.read()


def test_fetch_stock_price_uses_bearer_token_and_reads_current_price(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse({"success": True, "result": {"petr4": {"current_price": 38.52}}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    price = fetch_stock_price("petr4", token="kid.secret", base_url="https://api.sldx.test")

    assert price == 38.52
    assert captured["request"].full_url == "https://api.sldx.test/stock-price/PETR4"
    assert captured["request"].get_header("Authorization") == "Bearer kid.secret"
    assert captured["timeout"] == 4


def test_fetch_stock_price_rejects_missing_token():
    with pytest.raises(SldxMarketError, match="não configurado"):
        fetch_stock_price("PETR4", token="")


def test_fetch_stock_price_rejects_invalid_payload(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse({"result": {}}))
    with pytest.raises(SldxMarketError, match="cotação inválida"):
        fetch_stock_price("PETR4", token="kid.secret")


def test_fetch_option_chain_normalizes_only_valid_puts(monkeypatch):
    responses = iter([
        {
            "success": True,
            "result": {
                "underlying": "PETR4", "underlying_price": 41.94,
                "options": [
                    {"symbol":"PETRW420", "type":"PUT", "strike":42, "expiration_date":"2027-08-20", "bid":1.2, "ask":1.3, "last_price":1.25, "volume":5000, "implied_volatility":25},
                    {"symbol":"PETRH420", "type":"CALL", "strike":42, "expiration_date":"2027-08-20", "bid":1, "ask":1.1, "last_price":1.05, "volume":3000},
                ],
            },
        },
        {"success": True, "trade_date":"2026-08-14", "qty_contracts":2, "summary_by_expiration":[]},
    ])
    captured = []

    def fake_urlopen(request, timeout):
        captured.append(request.full_url)
        return FakeResponse(next(responses))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    rows = fetch_option_chain("PETR4", token="kid.secret", base_url="https://api.sldx.test")

    assert len(rows) == 1
    assert rows[0].option_code == "PETRW420"
    assert rows[0].option_type == "PUT"
    assert rows[0].spot_price == Decimal("41.94")
    assert rows[0].implied_volatility == Decimal("0.25")
    assert captured == [
        "https://api.sldx.test/stock-options-chain/PETR4",
        "https://api.sldx.test/stock-options/PETR4",
    ]


def test_fetch_options_market_keeps_successes_when_one_ticker_fails(monkeypatch):
    def fake_chain(symbol, **_kwargs):
        if symbol == "VALE3":
            raise SldxMarketError("indisponível")
        return (object(),)

    monkeypatch.setattr("services.sldx_market_service.fetch_option_chain", fake_chain)
    result = fetch_options_market(["PETR4", "VALE3"], token="kid.secret", max_workers=2)

    assert len(result.opportunities) == 1
    assert result.successful_tickers == ("PETR4",)
    assert result.failures == {"VALE3": "indisponível"}


def test_option_chain_can_select_calls_for_covered_call_scanner(monkeypatch):
    responses = iter([
        {"success": True, "result": {"underlying_price": 32, "options": [
            {"type": "PUT", "symbol": "PETRT300", "expiration_date": "2027-09-18", "strike": 30, "last_price": 0.4},
            {"type": "CALL", "symbol": "PETRI340", "expiration_date": "2027-09-18", "strike": 34, "last_price": 0.5},
        ]}},
        {"success": True, "trade_date": "2026-08-17"},
    ])
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse(next(responses)))
    calls = fetch_option_chain(
        "PETR4", token="kid.secret", base_url="https://api.sldx.test", option_types=("CALL",),
    )
    assert [item.option_code for item in calls] == ["PETRI340"]
    assert calls[0].option_type == "CALL"
