"""Importação de cadeia de opções por CSV para o Radar Premium."""
from __future__ import annotations

import csv
import io
import json
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from engine import OptionOpportunity
from engine.errors import DecisionEngineError


class MarketImportError(ValueError):
    """Erro de validação de arquivo de mercado."""


@dataclass(frozen=True, slots=True)
class MarketImportResult:
    opportunities: tuple[OptionOpportunity, ...]
    imported_at: datetime
    accepted_rows: int
    rejected_rows: int


ALIASES = {
    "option_code": {"opcao", "codigoopcao", "codigodaopcao", "optioncode", "tickeropcao", "ativoopcao"},
    "asset": {"ativo", "acao", "ativoobjeto", "underlying", "ticker", "papel"},
    "option_type": {"tipo", "tipodeopcao", "optiontype", "putcall"},
    "expiry": {"vencimento", "datavencimento", "expiry", "expiration", "expirationdate"},
    "spot_price": {"cotacao", "cotacaoativo", "precoativo", "spot", "spotprice", "underlyingprice"},
    "strike": {"strike", "precoexercicio", "exercicio"},
    "premium": {"premio", "precoopcao", "valoropcao", "ultimo", "last", "premium"},
    "bid": {"bid", "melhorcompra", "compra"},
    "ask": {"ask", "melhorvenda", "venda"},
    "liquidity": {"volume", "liquidez", "financialvolume", "negocios", "trades"},
}

REQUIRED = ("option_code", "asset", "expiry", "spot_price", "strike", "premium")


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return "".join(ch for ch in text.lower().strip() if ch.isalnum())


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise MarketImportError("Não foi possível identificar a codificação do CSV.")


def _delimiter(text: str) -> str:
    try:
        return csv.Sniffer().sniff(text[:4096], delimiters=";,\t|").delimiter
    except csv.Error:
        return ";" if text.count(";") >= text.count(",") else ","


def _column_map(fieldnames: Iterable[str]) -> dict[str, str]:
    normalized = {_normalize(name): name for name in fieldnames if name}
    mapped: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases | {_normalize(canonical)}:
            if alias in normalized:
                mapped[canonical] = normalized[alias]
                break
    missing = [field for field in REQUIRED if field not in mapped]
    if missing:
        labels = ", ".join(missing)
        raise MarketImportError(f"Colunas obrigatórias ausentes: {labels}.")
    return mapped


def _decimal(value: object, *, field: str) -> Decimal:
    text = str(value or "").replace("R$", "").replace("%", "").strip().replace(" ", "")
    if not text:
        raise MarketImportError(f"Campo {field} vazio.")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise MarketImportError(f"Valor inválido em {field}: {value}.") from exc
    if parsed < 0:
        raise MarketImportError(f"Valor negativo em {field}.")
    return parsed


def _optional_decimal(value: object) -> Decimal | None:
    if value in (None, "", "--"):
        return None
    try:
        return _decimal(value, field="opcional")
    except MarketImportError:
        return None


def _date(value: object) -> date:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise MarketImportError(f"Vencimento inválido: {value}.")


def parse_market_csv(data: bytes, *, as_of: date | None = None) -> MarketImportResult:
    if not data:
        raise MarketImportError("O arquivo CSV está vazio.")
    as_of = as_of or date.today()
    text = _decode(data)
    reader = csv.DictReader(io.StringIO(text), delimiter=_delimiter(text))
    if not reader.fieldnames:
        raise MarketImportError("O CSV não possui cabeçalho.")
    columns = _column_map(reader.fieldnames)
    opportunities: list[OptionOpportunity] = []
    rejected = 0
    for row in reader:
        try:
            option_type = str(row.get(columns.get("option_type", ""), "PUT") or "PUT").strip().upper()
            if option_type not in {"PUT", "P"}:
                rejected += 1
                continue
            expiry = _date(row[columns["expiry"]])
            if expiry < as_of:
                rejected += 1
                continue
            opportunity = OptionOpportunity(
                asset=str(row[columns["asset"]]).strip().upper(),
                option_code=str(row[columns["option_code"]]).strip().upper(),
                option_type="PUT",
                expiry=expiry,
                spot_price=_decimal(row[columns["spot_price"]], field="cotação do ativo"),
                strike=_decimal(row[columns["strike"]], field="strike"),
                premium=_decimal(row[columns["premium"]], field="prêmio"),
                bid=_optional_decimal(row.get(columns.get("bid", ""))),
                ask=_optional_decimal(row.get(columns.get("ask", ""))),
                liquidity=_optional_decimal(row.get(columns.get("liquidity", ""))),
                data_confidence=Decimal("0.80"),
                source="csv_importado",
            )
            opportunities.append(opportunity)
        except (KeyError, MarketImportError, DecisionEngineError, ValueError):
            rejected += 1
    if not opportunities:
        raise MarketImportError("Nenhuma PUT válida foi encontrada no arquivo.")
    return MarketImportResult(
        opportunities=tuple(opportunities),
        imported_at=datetime.now(),
        accepted_rows=len(opportunities),
        rejected_rows=rejected,
    )


def save_market_import(path: Path, result: MarketImportResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "imported_at": result.imported_at.isoformat(),
        "accepted_rows": result.accepted_rows,
        "rejected_rows": result.rejected_rows,
        "opportunities": [
            {
                "asset": item.asset,
                "option_code": item.option_code,
                "option_type": item.option_type,
                "expiry": item.expiry.isoformat(),
                "spot_price": str(item.spot_price),
                "strike": str(item.strike),
                "premium": str(item.premium),
                "bid": str(item.bid) if item.bid is not None else None,
                "ask": str(item.ask) if item.ask is not None else None,
                "liquidity": str(item.liquidity) if item.liquidity is not None else None,
                "data_confidence": str(item.data_confidence) if item.data_confidence is not None else None,
                "source": item.source,
            }
            for item in result.opportunities
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_market_import(path: Path) -> MarketImportResult | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    opportunities = tuple(
        OptionOpportunity(
            asset=item["asset"],
            option_code=item["option_code"],
            option_type="PUT",
            expiry=date.fromisoformat(item["expiry"]),
            spot_price=Decimal(item["spot_price"]),
            strike=Decimal(item["strike"]),
            premium=Decimal(item["premium"]),
            bid=Decimal(item["bid"]) if item.get("bid") is not None else None,
            ask=Decimal(item["ask"]) if item.get("ask") is not None else None,
            liquidity=Decimal(item["liquidity"]) if item.get("liquidity") is not None else None,
            data_confidence=Decimal(item["data_confidence"]) if item.get("data_confidence") else None,
            source=item.get("source", "csv_importado"),
        )
        for item in payload.get("opportunities", [])
    )
    if not opportunities:
        return None
    return MarketImportResult(
        opportunities=opportunities,
        imported_at=datetime.fromisoformat(payload["imported_at"]),
        accepted_rows=int(payload.get("accepted_rows", len(opportunities))),
        rejected_rows=int(payload.get("rejected_rows", 0)),
    )
