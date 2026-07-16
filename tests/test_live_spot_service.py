from services.live_spot_service import with_current_underlying_quotes


class FakeLegacy:
    @staticmethod
    def infer_acao_from_option(code):
        return "GOAU4" if str(code).startswith("GOAU") else "CPLE6"

    @staticmethod
    def cotacao_yahoo(ticker):
        return {"GOAU4": 10.52, "CPLE6": None}[ticker]


def test_live_quotes_override_stale_spot_and_keep_fallback_when_unavailable():
    operations = [
        {"Ativo": "GOAUS139", "Status": "Aberta", "Cotacao_n": 9.59},
        {"Ativo": "CPLES15", "Status": "Aberta", "Cotacao_n": 15.21},
    ]
    enriched = with_current_underlying_quotes(FakeLegacy, operations)
    assert enriched[0]["Cotacao_n"] == 10.52
    assert enriched[0]["Cotacao_fonte"] == "Yahoo Finance intradiário"
    assert enriched[1]["Cotacao_n"] == 15.21
    assert operations[0]["Cotacao_n"] == 9.59
