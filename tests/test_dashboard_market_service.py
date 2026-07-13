import json
from pathlib import Path

from services.dashboard_market_service import load_option_quotes


class FakeLegacy:
    DATA = Path("/tmp/not-used")
    RADAR_ASSETS = Path("/tmp/assets-not-used")
    RADAR_COTAHIST = Path("/tmp/cotahist-not-used")
    RADAR_QUOTES = Path("/tmp/quotes-not-used")

    @staticmethod
    def load_personal_asset_universe(_path):
        return (), {}


def test_manual_quote_has_priority(tmp_path):
    FakeLegacy.DATA = tmp_path
    FakeLegacy.RADAR_QUOTES = tmp_path / "manual_quotes.json"
    FakeLegacy.RADAR_QUOTES.write_text(json.dumps({"PETRT123": {"premium": "1.55"}}), encoding="utf-8")

    quotes = load_option_quotes(FakeLegacy)

    assert quotes["PETRT123"]["price"] == 1.55
    assert quotes["PETRT123"]["source"] == "preço manual confirmado"
