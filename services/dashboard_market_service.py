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


def save_underlying_quotes(legacy: Any, quotes: dict[str, float], source: str = "SLDX API") -> None:
    path = _underlying_path(legacy)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "quotes": {str(code).upper(): float(value) for code, value in quotes.items() if float(value) > 0},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_underlying_quotes(legacy: Any) -> dict[str, dict[str, object]]:
    quotes: dict[str, dict[str, object]] = {}
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
    quotes: dict[str, dict[str, object]] = {}
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
