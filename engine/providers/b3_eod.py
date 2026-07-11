"""Leitor determinístico dos arquivos públicos COTAHIST da B3."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping
from zipfile import ZipFile

from ..core.contracts import OptionOpportunity
from .base import MarketDataProvider, ProviderError


def _decimal(raw: str) -> Decimal:
    text = raw.strip() or "0"
    return Decimal(text) / Decimal("100")


def _integer(raw: str) -> int:
    return int(raw.strip() or "0")


class B3CotahistProvider(MarketDataProvider):
    """Normaliza PUTs EOD sem acoplar o Decision Engine ao formato posicional."""

    name = "b3_cotahist_eod"

    def __init__(self, source: str | Path, underlying_by_root: Mapping[str, str]):
        self.source = Path(source)
        self.underlying_by_root = {str(k).upper(): str(v).upper() for k, v in underlying_by_root.items()}

    def _lines(self) -> Iterable[str]:
        if not self.source.exists():
            raise ProviderError("Arquivo COTAHIST não encontrado", details={"path": str(self.source)})
        if self.source.suffix.lower() == ".zip":
            try:
                with ZipFile(self.source) as archive:
                    names = [name for name in archive.namelist() if name.lower().endswith(".txt")]
                    if not names:
                        raise ProviderError("ZIP da B3 não contém arquivo TXT")
                    with archive.open(names[0]) as stream:
                        for line in stream:
                            yield line.decode("latin-1").rstrip("\r\n")
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError("Não foi possível ler o ZIP COTAHIST", details={"error": str(exc)}) from exc
            return
        with self.source.open("r", encoding="latin-1") as stream:
            yield from (line.rstrip("\r\n") for line in stream)

    def fetch(self, request=None) -> tuple[OptionOpportunity, ...]:
        spots: dict[str, Decimal] = {}
        option_rows: list[dict[str, object]] = []
        for line in self._lines():
            if len(line) < 210 or line[:2] != "01":
                continue
            market_type = line[24:27]
            ticker = line[12:24].strip().upper()
            if market_type == "010" and ticker in self.underlying_by_root.values():
                spots[ticker] = _decimal(line[108:121])
                continue
            if market_type != "080":
                continue
            root = ticker[:4]
            asset = self.underlying_by_root.get(root)
            if not asset:
                continue
            expiry_text = line[202:210]
            try:
                trade_date = datetime.strptime(line[2:10], "%Y%m%d").date()
                expiry = datetime.strptime(expiry_text, "%Y%m%d").date()
            except ValueError:
                continue
            option_rows.append({
                "asset": asset,
                "ticker": ticker,
                "trade_date": trade_date,
                "expiry": expiry,
                "strike": _decimal(line[188:201]),
                "premium": _decimal(line[108:121]),
                "bid": _decimal(line[121:134]),
                "ask": _decimal(line[134:147]),
                "trades": _integer(line[147:152]),
                "volume": _integer(line[152:170]),
            })

        opportunities = []
        for row in option_rows:
            spot = spots.get(str(row["asset"]))
            if not spot or row["strike"] <= 0 or row["premium"] < 0:
                continue
            bid = row["bid"] if row["bid"] > 0 else None
            ask = row["ask"] if row["ask"] > 0 else None
            if bid is not None and ask is not None and ask < bid:
                bid = ask = None
            opportunities.append(OptionOpportunity(
                asset=str(row["asset"]), option_code=str(row["ticker"]), option_type="PUT",
                expiry=row["expiry"], spot_price=spot, strike=row["strike"], premium=row["premium"],
                bid=bid, ask=ask, volume=int(row["volume"]), trades=int(row["trades"]),
                liquidity=Decimal(int(row["volume"])),
                timestamp=datetime.combine(row["trade_date"], datetime.min.time(), tzinfo=timezone.utc),
                source=self.name, data_confidence=Decimal("0.80"),
            ))
        return tuple(opportunities)


def apply_intraday_quote(
    opportunity: OptionOpportunity, *, premium: Decimal, bid: Decimal | None = None, ask: Decimal | None = None
) -> OptionOpportunity:
    """Substitui apenas preços confirmados pelo usuário; dados estruturais permanecem EOD."""
    if premium < 0 or (bid is not None and bid < 0) or (ask is not None and ask < 0):
        raise ProviderError("Prêmios intraday não podem ser negativos")
    if bid is not None and ask is not None and ask < bid:
        raise ProviderError("Oferta de venda não pode ser menor que a oferta de compra")
    return replace(
        opportunity, premium=premium, bid=bid, ask=ask,
        timestamp=datetime.now(timezone.utc), source="manual_intraday", data_confidence=Decimal("0.95"),
    )
