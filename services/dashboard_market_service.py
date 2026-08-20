"""Option quotes available to the executive dashboard, without fabricating prices."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from services.market_import_service import load_market_import
from services.manual_option_quote_service import format_quote_source, load_manual_option_quotes


def _underlying_path(legacy: Any) -> Path:
    return Path(legacy.DATA) / "market" / "underlying_quotes.json"


def _ensure_api_quotes_table(cursor: Any) -> None:
    cursor.execute("""CREATE TABLE IF NOT EXISTS api_market_quotes (
        quote_kind TEXT NOT NULL,
        symbol TEXT NOT NULL,
        price NUMERIC NOT NULL,
        source TEXT NOT NULL,
        quoted_at TIMESTAMPTZ NOT NULL,
        PRIMARY KEY (quote_kind, symbol)
    )""")


def _save_api_quotes(legacy: Any, quote_kind: str, quotes: dict[str, float], source: str, quoted_at: datetime) -> None:
    if not getattr(legacy, "USE_POSTGRES", False) or not quotes:
        return
    connection = legacy.get_pg_conn()
    try:
        cursor = connection.cursor()
        _ensure_api_quotes_table(cursor)
        for symbol, price in quotes.items():
            cursor.execute("""INSERT INTO api_market_quotes(quote_kind, symbol, price, source, quoted_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(quote_kind, symbol) DO UPDATE SET
                price=EXCLUDED.price, source=EXCLUDED.source, quoted_at=EXCLUDED.quoted_at""",
                (quote_kind, str(symbol).upper(), float(price), source, quoted_at))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _load_api_quotes(legacy: Any, quote_kind: str) -> dict[str, dict[str, object]]:
    if not getattr(legacy, "USE_POSTGRES", False):
        return {}
    connection = legacy.get_pg_conn()
    try:
        cursor = connection.cursor()
        _ensure_api_quotes_table(cursor)
        connection.commit()
        cursor.execute(
            "SELECT symbol, price, source, quoted_at FROM api_market_quotes WHERE quote_kind=%s",
            (quote_kind,),
        )
        return {
            str(row[0]).upper(): {
                "price": float(row[1]), "source": str(row[2]),
                "quoted_at": row[3].isoformat(timespec="seconds") if row[3] else None,
            }
            for row in cursor.fetchall()
        }
    finally:
        connection.close()


def save_option_quotes(legacy: Any, opportunities: Any, quoted_at: datetime) -> None:
    """Persiste a última cotação da API para sobreviver aos reinícios do Render."""
    quotes = {
        str(item.option_code).upper(): float(item.premium)
        for item in opportunities if float(item.premium) >= 0
    }
    _save_api_quotes(legacy, "option", quotes, "SLDX API", quoted_at)


def save_underlying_quotes(legacy: Any, quotes: dict[str, float], source: str = "SLDX API") -> None:
    path = _underlying_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "quotes": {str(code).upper(): float(value) for code, value in quotes.items() if float(value) > 0},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _save_api_quotes(legacy, "underlying", payload["quotes"], source, datetime.fromisoformat(payload["updated_at"]))


def load_underlying_quotes(legacy: Any) -> dict[str, dict[str, object]]:
    quotes: dict[str, dict[str, object]] = _load_api_quotes(legacy, "underlying")
    imported = load_market_import(Path(legacy.DATA) / "market" / "imported_options.json")
    if imported:
        for opportunity in imported.opportunities:
            quotes[opportunity.asset.upper()] = {
                "price": float(opportunity.spot_price),
                "source": "SLDX API",
                "quoted_at": imported.imported_at.isoformat(timespec="seconds"),
            }
    path = _underlying_path(legacy)
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for code, price in payload.get("quotes", {}).items():
            quotes[str(code).upper()] = {
                "price": float(price), "source": payload.get("source", "SLDX API"),
                "quoted_at": payload.get("updated_at"),
            }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return quotes


def load_option_quotes(legacy: Any) -> dict[str, dict[str, object]]:
    quotes: dict[str, dict[str, object]] = _load_api_quotes(legacy, "option")
    imported_path = Path(legacy.DATA) / "market" / "imported_options.json"
    imported = load_market_import(imported_path)
    if imported:
        for opportunity in imported.opportunities:
            quotes[opportunity.option_code.upper()] = {
                "price": float(opportunity.premium),
                "source": "SLDX API" if opportunity.source == "sldx_api" else (opportunity.source or "mercado importado"),
            }
    try:
        roots, _profiles = legacy.load_personal_asset_universe(legacy.RADAR_ASSETS)
        if legacy.RADAR_COTAHIST.exists() and roots and not quotes:
            for opportunity in legacy.B3CotahistProvider(legacy.RADAR_COTAHIST, roots).fetch():
                quotes.setdefault(opportunity.option_code.upper(), {
                    "price": float(opportunity.premium), "source": "B3 COTAHIST EOD"
                })
    except Exception:
        pass
    try:
        overrides = json.loads(legacy.RADAR_QUOTES.read_text(encoding="utf-8")) if legacy.RADAR_QUOTES.exists() else {}
        for code, quote in overrides.items():
            quotes.setdefault(str(code).upper(), {"price": float(quote["premium"]), "source": "preço manual confirmado"})
    except Exception:
        pass
    try:
        for code, quote in load_manual_option_quotes(legacy).items():
            quotes.setdefault(str(code).upper(), {
                "price": float(quote["price"]),
                "source": format_quote_source(quote),
                "manual": True,
                "quoted_at": quote.get("quoted_at"),
            })
    except Exception:
        pass
    return quotes
