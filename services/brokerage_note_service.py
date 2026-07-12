"""Leitura e consolidação de notas de corretagem BTG/Necton.

O PDF nunca é persistido. Somente dados estruturados, hash e vínculo com a
operação confirmada pelo usuário são armazenados.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pypdf import PdfReader


MAX_NOTE_SIZE = 5 * 1024 * 1024


class BrokerageNoteError(ValueError):
    pass


def _money(value: str | Decimal | int | float | None) -> Decimal:
    text = str(value or "0").strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise BrokerageNoteError(f"Valor monetário inválido: {value}") from exc


def _brl(value: Decimal) -> str:
    return f"R$ {value.quantize(Decimal('0.01')):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _extract_amount(text: str, label: str, *, after: bool = False) -> Decimal | None:
    amount = r"([0-9.]+,[0-9]{2})"
    pattern = rf"{re.escape(label)}[^\n]{{0,35}}?{amount}" if after else rf"{amount}\s*{re.escape(label)}"
    match = re.search(pattern, text, re.IGNORECASE)
    return _money(match.group(1)) if match else None


@dataclass(frozen=True)
class ParsedTrade:
    trade_index: int
    option_code: str
    side: str
    market: str
    expiry_month: str
    quantity: int
    contracts: Decimal
    unit_price: Decimal
    gross_value: Decimal
    cash_direction: str
    allocated_costs: Decimal
    allocated_irrf: Decimal


@dataclass(frozen=True)
class ParsedBrokerageNote:
    broker: str
    note_number: str
    trade_date: date
    settlement_date: date | None
    document_hash: str
    gross_operations: Decimal
    net_cash: Decimal
    operational_costs: Decimal
    irrf: Decimal
    cash_direction: str
    trades: tuple[ParsedTrade, ...]


def extract_pdf_text(data: bytes) -> str:
    if not data:
        raise BrokerageNoteError("O PDF está vazio.")
    if len(data) > MAX_NOTE_SIZE:
        raise BrokerageNoteError("A nota deve ter no máximo 5 MB.")
    try:
        from io import BytesIO
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise BrokerageNoteError("Não foi possível ler o PDF.") from exc
    if not text.strip():
        raise BrokerageNoteError("O PDF não possui texto pesquisável.")
    return text


def parse_btg_necton_pdf(data: bytes) -> ParsedBrokerageNote:
    text = extract_pdf_text(data)
    normalized = " ".join(text.upper().split())
    if "NOTA DE CORRETAGEM" not in normalized or ("BTG PACTUAL" not in normalized and "NECTON" not in normalized):
        raise BrokerageNoteError("Envie uma nota de corretagem BTG/Necton válida.")

    note_match = re.search(r"NOTA DE CORRETAGEM\s+(\d{5,})", text, re.IGNORECASE)
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+Data pregão", text, re.IGNORECASE)
    if not note_match or not date_match:
        raise BrokerageNoteError("Número ou data do pregão não foram reconhecidos.")
    trade_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()

    section = text.split("Negócios realizados", 1)[-1].split("Resumo dos Negócios", 1)[0]
    pattern = re.compile(
        r"1-BOVESPA\s+([CV])\s+OPCAO DE (VENDA|COMPRA)\s+(\d{2}/\d{2})\s+([A-Z0-9]+)"
        r"(?:\s+[A-Z]{1,4})?\s+(\d+)\s+([0-9.,]+)\s+([0-9.,]+)\s+([CD])",
        re.IGNORECASE,
    )
    raw_trades = list(pattern.finditer(section))
    if not raw_trades:
        raise BrokerageNoteError("Nenhuma operação de opção foi reconhecida na nota.")

    gross = _extract_amount(text, "Valor das operações") or sum((_money(m.group(7)) for m in raw_trades), Decimal("0"))
    settlement = re.search(r"Líquido para\s+(\d{2}/\d{2}/\d{4})\s+([CD])\s*([0-9.,]+)", text, re.IGNORECASE)
    if not settlement:
        settlement = re.search(r"Líquido para\s+(\d{2}/\d{2}/\d{4})\s*([CD])?\s*([0-9.,]+)", text, re.IGNORECASE)
    settlement_date = datetime.strptime(settlement.group(1), "%d/%m/%Y").date() if settlement else None
    direction = (settlement.group(2) or raw_trades[0].group(8)).upper() if settlement else raw_trades[0].group(8).upper()
    net = _money(settlement.group(3)) if settlement else gross
    irrf = _extract_amount(text, "I.R.R.F. s/ operações, base R$", after=True) or Decimal("0")
    effective_costs = abs(gross - net)
    total_trade_value = sum((_money(match.group(7)) for match in raw_trades), Decimal("0")) or Decimal("1")

    trades = []
    for index, match in enumerate(raw_trades):
        value = _money(match.group(7))
        share = value / total_trade_value
        quantity = int(match.group(5))
        trades.append(ParsedTrade(
            trade_index=index,
            option_code=match.group(4).upper(),
            side="Venda" if match.group(1).upper() == "V" else "Compra",
            market=f"Opção de {match.group(2).lower()}",
            expiry_month=match.group(3),
            quantity=quantity,
            contracts=Decimal(quantity) / Decimal("100"),
            unit_price=_money(match.group(6)),
            gross_value=value,
            cash_direction=match.group(8).upper(),
            allocated_costs=(effective_costs * share).quantize(Decimal("0.01")),
            allocated_irrf=(irrf * share).quantize(Decimal("0.01")),
        ))

    return ParsedBrokerageNote(
        broker="BTG Pactual / Necton",
        note_number=note_match.group(1),
        trade_date=trade_date,
        settlement_date=settlement_date,
        document_hash=hashlib.sha256(data).hexdigest(),
        gross_operations=gross,
        net_cash=net,
        operational_costs=effective_costs,
        irrf=irrf,
        cash_direction=direction,
        trades=tuple(trades),
    )


def note_to_api(note: ParsedBrokerageNote) -> dict[str, Any]:
    return {
        "broker": note.broker,
        "note_number": note.note_number,
        "trade_date": note.trade_date.isoformat(),
        "settlement_date": note.settlement_date.isoformat() if note.settlement_date else None,
        "document_hash": note.document_hash,
        "gross_operations": str(note.gross_operations),
        "net_cash": str(note.net_cash),
        "operational_costs": str(note.operational_costs),
        "irrf": str(note.irrf),
        "cash_direction": note.cash_direction,
        "trades": [{**asdict(trade), "contracts": str(trade.contracts), "unit_price": str(trade.unit_price), "gross_value": str(trade.gross_value), "allocated_costs": str(trade.allocated_costs), "allocated_irrf": str(trade.allocated_irrf)} for trade in note.trades],
    }


def _storage_path(legacy) -> Path:
    return legacy.DATA / "brokerage_notes.json"


def load_imported_notes(legacy) -> list[dict[str, Any]]:
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS brokerage_notes (
                note_key TEXT PRIMARY KEY, payload JSONB NOT NULL, imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            conn.commit()
            cur.execute("SELECT payload FROM brokerage_notes ORDER BY imported_at DESC")
            rows = cur.fetchall()
            return [row[0] if isinstance(row[0], dict) else json.loads(row[0]) for row in rows]
        finally:
            conn.close()
    path = _storage_path(legacy)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []
    except Exception:
        return []


def save_imported_note(legacy, payload: dict[str, Any], operation_id: str) -> bool:
    required = {"document_hash", "note_number", "trade_date", "broker", "trade"}
    if not required.issubset(payload):
        raise BrokerageNoteError("Dados da nota incompletos.")
    trade = payload["trade"]
    key = f"{payload['document_hash']}:{int(trade.get('trade_index', 0))}"
    record = {
        "key": key,
        "document_hash": str(payload["document_hash"]),
        "note_number": str(payload["note_number"]),
        "broker": "BTG Pactual / Necton",
        "trade_date": str(payload["trade_date"]),
        "settlement_date": payload.get("settlement_date"),
        "cash_direction": str(payload.get("cash_direction", "C")),
        "gross_operations": str(_money(payload.get("gross_operations"))),
        "net_cash": str(_money(payload.get("net_cash"))),
        "operational_costs": str(_money(payload.get("operational_costs"))),
        "irrf": str(_money(payload.get("irrf"))),
        "trade": trade,
        "operation_id": str(operation_id),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS brokerage_notes (
                note_key TEXT PRIMARY KEY, payload JSONB NOT NULL, imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cur.execute(
                "INSERT INTO brokerage_notes (note_key, payload) VALUES (%s, %s::jsonb) ON CONFLICT (note_key) DO NOTHING",
                (key, json.dumps(record, ensure_ascii=False)),
            )
            inserted = cur.rowcount > 0
            conn.commit()
            return inserted
        finally:
            conn.close()
    rows = load_imported_notes(legacy)
    if any(row.get("key") == key for row in rows):
        return False
    rows.append(record)
    path = _storage_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return True


def imported_note_exists(legacy, payload: dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("trade"), dict):
        return False
    key = f"{payload.get('document_hash', '')}:{int(payload['trade'].get('trade_index', 0))}"
    return any(row.get("key") == key for row in load_imported_notes(legacy))


def last_business_day_next_month(year: int, month: int) -> date:
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    candidate = date(next_year, next_month, calendar.monthrange(next_year, next_month)[1])
    while candidate.weekday() >= 5:
        candidate -= timedelta(days=1)
    return candidate


def build_notes_dashboard(notes: list[dict[str, Any]]) -> dict[str, Any]:
    monthly: dict[str, dict[str, Decimal]] = {}
    for note in notes:
        month = str(note.get("trade_date", ""))[:7]
        if not month:
            continue
        bucket = monthly.setdefault(month, {"credits": Decimal("0"), "trade_debits": Decimal("0"), "costs": Decimal("0"), "irrf": Decimal("0")})
        direction = str(note.get("cash_direction", "C")).upper()
        net = _money(note.get("net_cash"))
        if direction == "C":
            bucket["credits"] += net
        else:
            bucket["trade_debits"] += net
        bucket["costs"] += _money(note.get("operational_costs"))
        bucket["irrf"] += _money(note.get("irrf"))
    months = sorted(monthly)[-12:]
    year = str(date.today().year)
    year_rows = [value for key, value in monthly.items() if key.startswith(year)]
    totals = {name: sum((row[name] for row in year_rows), Decimal("0")) for name in ("credits", "trade_debits", "costs", "irrf")}
    current_key = date.today().strftime("%Y-%m")
    current = monthly.get(current_key, {name: Decimal("0") for name in ("credits", "trade_debits", "costs", "irrf")})
    return {
        "notes": list(reversed(notes)),
        "count": len(notes),
        "months": months,
        "credit_series": [float(monthly[m]["credits"]) for m in months],
        "cost_series": [float(monthly[m]["costs"] + monthly[m]["irrf"]) for m in months],
        "totals": totals,
        "current": current,
        "monthly": monthly,
        "darf_estimate": Decimal("0"),
        "darf_due": None,
        "darf_note": "Créditos de abertura de PUT não são lucro realizado. A estimativa só será liberada após identificar fechamento, exercício ou expiração e eventuais prejuízos compensáveis.",
    }
