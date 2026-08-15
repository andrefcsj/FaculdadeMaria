import json
from io import BytesIO

import pytest

from services.sldx_market_service import SldxMarketError, fetch_stock_price


class FakeResponse:
    def __init__(self, payload):
        self.body = BytesIO(json.dumps(payload).encode("utf-8"))
    def __enter__(self): return self
    def __exit__(self, *_args): return None
    def read(self): return self.body.read()


def test_fetch_stock_price_uses_bearer_token_and_reads_current_price(monkeypatch):
    captured = {}
    def fake_urlopen(request, timeout):
        captured.update(request=request, timeout=timeout)
        return FakeResponse({"success": True, "result": {"petr4": {"current_price": 38.52}}})
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    price = fetch_stock_price("petr4", token="kid.secret", base_url="https://api.sldx.test")
    assert price == 38.52
    assert captured["request"].full_url == "https://api.sldx.test/stock-price/PETR4"
    assert captured["request"].get_header("Authorization") == "Bearer kid.secret"


def test_fetch_stock_price_rejects_missing_token():
    with pytest.raises(SldxMarketError, match="não configurado"):
        fetch_stock_price("PETR4", token="")


def test_fetch_stock_price_rejects_invalid_payload(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: FakeResponse({"result": {}}))
    with pytest.raises(SldxMarketError, match="cotação inválida"):
        fetch_stock_price("PETR4", token="kid.secret")
