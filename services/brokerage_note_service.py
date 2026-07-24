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


def _option_market_from_code(code: str) -> str:
    """Infere CALL/PUT pela letra de vencimento do código B3."""
    normalized = str(code or "").upper()
    month_letter = normalized[4:5]
    if month_letter in "ABCDEFGHIJKL":
        return "Opção de compra"
    if month_letter in "MNOPQRSTUVWX":
        return "Opção de venda"
    return "Opção"


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
    event_type: str = "trade"
    underlying_asset: str = ""


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
    is_provisional: bool = False


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

    document_hash = hashlib.sha256(data).hexdigest()
    note_match = re.search(r"NOTA DE CORRETAGEM\s+(\d{5,})", text, re.IGNORECASE)
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})[^\n]{0,80}Data pregão", text, re.IGNORECASE)
    if not date_match:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    if not date_match:
        raise BrokerageNoteError("A data do pregão não foi reconhecida.")
    trade_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()

    # Exercício do lançador de PUT. A nota prévia não traz número e o sufixo E
    # identifica o exercício, não faz parte do código negociado da opção.
    exercise_match = re.search(
        r"1-BOVESPA\s+C\s+EOV\s+([A-Z0-9]+)\s+(\d+)\s+([0-9.,]+)\s+([0-9.,]+)\s+D",
        text, re.IGNORECASE,
    )
    if exercise_match:
        raw_code = exercise_match.group(1).upper()
        option_code = raw_code[:-1] if raw_code.endswith("E") else raw_code
        quantity = int(exercise_match.group(2))
        unit_price = _money(exercise_match.group(3))
        gross = _money(exercise_match.group(4))
        liquid = re.search(r"Líquido:\s*D\s*([0-9.,]+)", text, re.IGNORECASE)
        net = _money(liquid.group(1)) if liquid else gross
        irrf = _extract_amount(text, "I.R.R.F. s/ operações, base R$", after=True) or Decimal("0")
        costs = max(net - gross - irrf, Decimal("0"))
        trade = ParsedTrade(
            trade_index=0, option_code=option_code, side="Compra",
            market="Exercício de PUT vendida", expiry_month="",
            quantity=quantity, contracts=Decimal(quantity) / Decimal("100"),
            unit_price=unit_price, gross_value=gross, cash_direction="D",
            allocated_costs=costs, allocated_irrf=irrf,
            event_type="exercise_put_assignment",
        )
        return ParsedBrokerageNote(
            broker="BTG Pactual / Necton",
            note_number=note_match.group(1) if note_match else f"EXERCICIO-{trade_date:%Y%m%d}-{document_hash[:8].upper()}",
            trade_date=trade_date, settlement_date=trade_date,
            document_hash=document_hash, gross_operations=gross, net_cash=net,
            operational_costs=costs, irrf=irrf, cash_direction="D", trades=(trade,),
            is_provisional=note_match is None,
        )

    provisional_number = f"PREVIA-{trade_date:%Y%m%d}-{document_hash[:8].upper()}"

    section = text.split("Negócios realizados", 1)[-1].split("Resumo dos Negócios", 1)[0]
    pattern = re.compile(
        r"1-BOVESPA\s+([CV])\s+OPCAO DE (VENDA|COMPRA)\s+(\d{2}/\d{2})\s+([A-Z0-9]+)"
        r"(?:\s+[A-Z]{1,4})?\s+(\d+)\s+([0-9.,]+)\s+([0-9.,]+)\s+([CD])",
        re.IGNORECASE,
    )
    raw_trades = list(pattern.finditer(section))
    # A nota intradiária/prévia do BTG usa um layout resumido, por exemplo:
    # ``1-BOVESPA V OPÇÃO PETRT500 100 1,53 153,00 C``. Ela não informa o
    # subtipo (compra/venda) nem o vencimento textual, mas traz todos os dados
    # financeiros necessários para cadastrar a negociação como pendente.
    provisional_option_pattern = re.compile(
        r"1-BOVESPA\s+([CV])\s+OP(?:Ç|C)[AÃ]O\s+([A-Z0-9]+)"
        r"\s+(\d+)\s+([0-9.,]+)\s+([0-9.,]+)\s+([CD])",
        re.IGNORECASE,
    )
    provisional_option_trades = list(provisional_option_pattern.finditer(section))
    equity_pattern = re.compile(
        r"1-BOVESPA\s+([CV])\s+(?:VISTA|FRACIONARIO)\s+([A-Z]{4}\d{1,2})"
        r"(?:\s+[A-Z0-9.*-]+){0,5}?\s+(\d+)\s+([0-9.,]+)\s+([0-9.,]+)\s+([CD])",
        re.IGNORECASE,
    )
    equity_trades = list(equity_pattern.finditer(section))
    entries: list[dict[str, Any]] = []
    for match in raw_trades:
        entries.append({
            "code": match.group(4).upper(), "side": "Venda" if match.group(1).upper() == "V" else "Compra",
            "market": f"Opção de {match.group(2).lower()}", "expiry_month": match.group(3),
            "quantity": int(match.group(5)), "unit_price": _money(match.group(6)),
            "value": _money(match.group(7)), "direction": match.group(8).upper(),
            "event_type": "trade", "underlying": "",
        })
    for match in provisional_option_trades:
        entries.append({
            "code": match.group(2).upper(),
            "side": "Venda" if match.group(1).upper() == "V" else "Compra",
            "market": _option_market_from_code(match.group(2)), "expiry_month": "",
            "quantity": int(match.group(3)), "unit_price": _money(match.group(4)),
            "value": _money(match.group(5)), "direction": match.group(6).upper(),
            "event_type": "trade", "underlying": "",
        })
    for match in equity_trades:
        ticker = match.group(2).upper()
        entries.append({
            "code": ticker, "side": "Venda" if match.group(1).upper() == "V" else "Compra",
            "market": "Mercado à vista", "expiry_month": "", "quantity": int(match.group(3)),
            "unit_price": _money(match.group(4)), "value": _money(match.group(5)),
            "direction": match.group(6).upper(), "event_type": "equity_purchase" if match.group(1).upper() == "C" else "equity_sale",
            "underlying": ticker,
        })
    if not entries:
        raise BrokerageNoteError("Nenhuma operação de opção ou ação foi reconhecida na nota.")

    # Preserva a ordem em que as negociações aparecem no PDF.
    entries.sort(key=lambda entry: section.find(entry["code"]))
    gross = _extract_amount(text, "Valor das operações") or sum((entry["value"] for entry in entries), Decimal("0"))
    settlement = re.search(r"Líquido para\s+(\d{2}/\d{2}/\d{4})\s+([CD])\s*([0-9.,]+)", text, re.IGNORECASE)
    if not settlement:
        settlement = re.search(r"Líquido para\s+(\d{2}/\d{2}/\d{4})\s*([CD])?\s*([0-9.,]+)", text, re.IGNORECASE)
    settlement_date = datetime.strptime(settlement.group(1), "%d/%m/%Y").date() if settlement else None
    liquid_summary = re.search(r"Líquido:\s*([CD])\s*([0-9.,]+)", text, re.IGNORECASE)
    direction = (
        (settlement.group(2) or entries[0]["direction"]).upper()
        if settlement else
        liquid_summary.group(1).upper() if liquid_summary else entries[0]["direction"]
    )
    net = (
        _money(settlement.group(3)) if settlement else
        _money(liquid_summary.group(2)) if liquid_summary else gross
    )
    irrf = _extract_amount(text, "I.R.R.F. s/ operações, base R$", after=True) or Decimal("0")
    signed_trades = sum((entry["value"] if entry["direction"] == "C" else -entry["value"] for entry in entries), Decimal("0"))
    signed_net = net if direction == "C" else -net
    total_deductions = abs(signed_trades - signed_net)
    effective_costs = max(total_deductions - irrf, Decimal("0"))
    total_trade_value = sum((entry["value"] for entry in entries), Decimal("0")) or Decimal("1")

    trades = []
    allocated_costs_total = Decimal("0")
    allocated_irrf_total = Decimal("0")
    for index, entry in enumerate(entries):
        value = entry["value"]
        share = value / total_trade_value
        quantity = entry["quantity"]
        is_last = index == len(entries) - 1
        allocated_costs = (
            effective_costs - allocated_costs_total
            if is_last
            else (effective_costs * share).quantize(Decimal("0.01"))
        )
        allocated_irrf = (
            irrf - allocated_irrf_total
            if is_last
            else (irrf * share).quantize(Decimal("0.01"))
        )
        allocated_costs_total += allocated_costs
        allocated_irrf_total += allocated_irrf
        trades.append(ParsedTrade(
            trade_index=index,
            option_code=entry["code"],
            side=entry["side"],
            market=entry["market"],
            expiry_month=entry["expiry_month"],
            quantity=quantity,
            contracts=Decimal(quantity) / Decimal("100"),
            unit_price=entry["unit_price"],
            gross_value=value,
            cash_direction=entry["direction"],
            allocated_costs=allocated_costs,
            allocated_irrf=allocated_irrf,
            event_type=entry["event_type"],
            underlying_asset=entry["underlying"],
        ))

    return ParsedBrokerageNote(
        broker="BTG Pactual / Necton",
        note_number=note_match.group(1) if note_match else provisional_number,
        trade_date=trade_date,
        settlement_date=settlement_date,
        document_hash=document_hash,
        gross_operations=gross,
        net_cash=net,
        operational_costs=effective_costs,
        irrf=irrf,
        cash_direction=direction,
        trades=tuple(trades), is_provisional=note_match is None,
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
        "is_provisional": note.is_provisional,
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


def _trade_identity(payload: dict[str, Any]) -> tuple[str, ...]:
    trade = payload.get("trade", {}) if isinstance(payload, dict) else {}
    return (
        str(payload.get("trade_date", ""))[:10],
        str(trade.get("event_type", "trade")).strip().lower(),
        str(trade.get("underlying_asset") or trade.get("option_code") or "").strip().upper(),
        str(trade.get("side", "")).strip().lower(),
        str(int(trade.get("quantity", 0) or 0)),
    )


def find_matching_provisional_note(legacy, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Devolve apenas uma prévia inequivocamente correspondente à definitiva."""
    if bool(payload.get("is_provisional", False)):
        return None
    identity = _trade_identity(payload)
    candidates = [
        row for row in load_imported_notes(legacy)
        if bool(row.get("is_provisional", False)) and _trade_identity(row) == identity
    ]
    return candidates[0] if len(candidates) == 1 else None


def _build_note_record(payload: dict[str, Any], operation_id: str) -> dict[str, Any]:
    trade = payload["trade"]
    key = f"{payload['document_hash']}:{int(trade.get('trade_index', 0))}"
    has_trade_values = trade.get("gross_value") not in (None, "")
    trade_gross = _money(trade.get("gross_value")) if has_trade_values else _money(payload.get("gross_operations"))
    trade_costs = _money(trade.get("allocated_costs")) if has_trade_values else _money(payload.get("operational_costs"))
    trade_irrf = _money(trade.get("allocated_irrf")) if has_trade_values else _money(payload.get("irrf"))
    trade_direction = str(trade.get("cash_direction") or "").upper()
    if trade_direction not in {"C", "D"}:
        trade_side = str(trade.get("side", "")).lower()
        trade_direction = "C" if trade_side == "venda" else "D" if trade_side == "compra" else str(payload.get("cash_direction", "C")).upper()
    trade_net = trade_gross - trade_costs - trade_irrf if trade_direction == "C" else trade_gross + trade_costs + trade_irrf
    return {
        "key": key, "document_hash": str(payload["document_hash"]),
        "note_number": str(payload["note_number"]),
        "is_provisional": bool(payload.get("is_provisional", False)),
        "broker": "BTG Pactual / Necton", "trade_date": str(payload["trade_date"]),
        "settlement_date": payload.get("settlement_date"),
        "cash_direction": trade_direction, "gross_operations": str(trade_gross),
        "net_cash": str(trade_net), "operational_costs": str(trade_costs),
        "irrf": str(trade_irrf), "trade": trade,
        "operation_id": str(operation_id),
        "imported_at": datetime.now().isoformat(timespec="seconds"),
    }


def replace_provisional_note(legacy, provisional_key: str, payload: dict[str, Any], operation_id: str) -> bool:
    """Substitui uma prévia pela definitiva, sem manter os dois lançamentos."""
    record = _build_note_record(payload, operation_id)
    new_key = record["key"]
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS brokerage_notes (
                note_key TEXT PRIMARY KEY, payload JSONB NOT NULL, imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
            cur.execute("SELECT 1 FROM brokerage_notes WHERE note_key=%s", (new_key,))
            if cur.fetchone():
                return False
            cur.execute("DELETE FROM brokerage_notes WHERE note_key=%s", (str(provisional_key),))
            if cur.rowcount != 1:
                conn.rollback()
                return False
            cur.execute(
                "INSERT INTO brokerage_notes (note_key,payload) VALUES (%s,%s::jsonb)",
                (new_key, json.dumps(record, ensure_ascii=False)),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    rows = load_imported_notes(legacy)
    index = next((i for i, row in enumerate(rows) if str(row.get("key")) == str(provisional_key)), None)
    if index is None or any(str(row.get("key")) == new_key for row in rows):
        return False
    rows[index] = record
    path = _storage_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return True


def save_imported_note(legacy, payload: dict[str, Any], operation_id: str) -> bool:
    required = {"document_hash", "note_number", "trade_date", "broker", "trade"}
    if not required.issubset(payload):
        raise BrokerageNoteError("Dados da nota incompletos.")
    record = _build_note_record(payload, operation_id)
    key = record["key"]
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


def delete_imported_note(legacy, note_key: str) -> bool:
    key = str(note_key or "").strip()
    if not key:
        return False
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM brokerage_notes WHERE note_key=%s", (key,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            conn.close()
    rows = load_imported_notes(legacy)
    kept = [row for row in rows if str(row.get("key", "")) != key]
    if len(kept) == len(rows):
        return False
    path = _storage_path(legacy)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return True


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
