from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from engine.providers.b3_eod import B3CotahistProvider, apply_intraday_quote
from engine import AssetQualityProfile
from services.radar_service import build_radar_from_market


def _line(*, ticker, market, close, bid=0, ask=0, trades=1, quantity=100, strike=0, expiry="00000000", day="20260710"):
    line = [" "] * 245
    def put(start, end, value):
        line[start:end] = list(str(value).ljust(end-start)[:end-start])
    put(0, 2, "01"); put(2, 10, day); put(12, 24, ticker); put(24, 27, market)
    put(108, 121, str(int(Decimal(str(close))*100)).zfill(13))
    put(121, 134, str(int(Decimal(str(bid))*100)).zfill(13))
    put(134, 147, str(int(Decimal(str(ask))*100)).zfill(13))
    put(147, 152, str(trades).zfill(5)); put(152, 170, str(quantity).zfill(18))
    put(188, 201, str(int(Decimal(str(strike))*100)).zfill(13)); put(202, 210, expiry)
    return "".join(line)


class B3EodProviderTests(unittest.TestCase):
  def test_reads_put_and_underlying_from_official_fixed_width_layout(self):
    rows = [
        _line(ticker="PETR4", market="010", close="32.50"),
        _line(ticker="PETRQ300", market="080", close="1.20", bid="1.15", ask="1.25", trades=42,
              quantity=12000, strike="30", expiry="20260821"),
    ]
    with TemporaryDirectory() as folder:
        path = Path(folder) / "COTAHIST_D.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr("COTAHIST_D.TXT", "\n".join(rows))
        result = B3CotahistProvider(path, {"PETR": "PETR4"}).fetch()
    self.assertEqual(len(result), 1)
    option = result[0]
    self.assertEqual(option.asset, "PETR4")
    self.assertEqual(option.option_type, "PUT")
    self.assertEqual(option.strike, Decimal("30"))
    self.assertEqual(option.premium, Decimal("1.2"))
    self.assertEqual(option.bid, Decimal("1.15"))
    self.assertEqual(option.ask, Decimal("1.25"))
    self.assertEqual(option.expiry, date(2026, 8, 21))
    self.assertEqual(option.source, "b3_cotahist_eod")


  def test_manual_quote_preserves_contract_and_replaces_only_market_price(self):
    rows = [
        _line(ticker="PETR4", market="010", close="32.50"),
        _line(ticker="PETRQ300", market="080", close="1.20", strike="30", expiry="20260821"),
    ]
    with TemporaryDirectory() as folder:
        path = Path(folder) / "COTAHIST.TXT"
        path.write_text("\n".join(rows), encoding="latin-1")
        option = B3CotahistProvider(path, {"PETR": "PETR4"}).fetch()[0]
    updated = apply_intraday_quote(option, premium=Decimal("1.55"), bid=Decimal("1.50"), ask=Decimal("1.60"))
    self.assertEqual(updated.option_code, option.option_code)
    self.assertEqual(updated.strike, option.strike)
    self.assertEqual(updated.premium, Decimal("1.55"))
    self.assertEqual(updated.source, "manual_intraday")

  def test_provider_output_enters_engine_and_unknown_asset_is_blocked(self):
    rows = [
        _line(ticker="PETR4", market="010", close="32.50"),
        _line(ticker="PETRQ300", market="080", close="1.20", bid="1.15", ask="1.25", trades=42,
              quantity=12000, strike="30", expiry="20260821"),
    ]
    with TemporaryDirectory() as folder:
        path = Path(folder) / "COTAHIST.TXT"
        path.write_text("\n".join(rows), encoding="latin-1")
        options = B3CotahistProvider(path, {"PETR": "PETR4"}).fetch()
    cards = build_radar_from_market(options, {}, date(2026, 7, 10))
    self.assertEqual(len(cards), 1)
    self.assertEqual(cards[0].status, "discarded")
    self.assertIn("exercício", cards[0].reason.lower())
