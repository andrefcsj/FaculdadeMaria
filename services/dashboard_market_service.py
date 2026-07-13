"""Option quotes available to the executive dashboard, without fabricating prices."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.market_import_service import load_market_import


def load_option_quotes(legacy: Any) -> dict[str, dict[str, object]]:
    quotes: dict[str, dict[str, object]] = {}
    imported_path = Path(legacy.DATA) / "market" / "imported_options.json"
    imported = load_market_import(imported_path)
    if imported:
        for opportunity in imported.opportunities:
            quotes[opportunity.option_code.upper()] = {
                "price": float(opportunity.premium), "source": opportunity.source or "mercado importado"
            }
    try:
        roots, _profiles = legacy.load_personal_asset_universe(legacy.RADAR_ASSETS)
        if legacy.RADAR_COTAHIST.exists() and roots:
            for opportunity in legacy.B3CotahistProvider(legacy.RADAR_COTAHIST, roots).fetch():
                quotes[opportunity.option_code.upper()] = {
                    "price": float(opportunity.premium), "source": "B3 COTAHIST EOD"
                }
    except Exception:
        pass
    try:
        overrides = json.loads(legacy.RADAR_QUOTES.read_text(encoding="utf-8")) if legacy.RADAR_QUOTES.exists() else {}
        for code, quote in overrides.items():
            quotes[str(code).upper()] = {"price": float(quote["premium"]), "source": "preço manual confirmado"}
    except Exception:
        pass
    return quotes
