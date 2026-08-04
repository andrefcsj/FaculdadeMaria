"""Rotas do módulo Radar Jade Lizard."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
import re

from flask import jsonify, render_template, request

from services.jade_lizard_service import JadeConfig, scan_estimated_chain


REFERENCE_SPOTS = {
    "PETR4": 37.0, "VALE3": 62.0, "ITUB4": 36.0, "BBAS3": 28.0, "BBDC4": 15.0,
    "ITSA4": 11.0, "B3SA3": 13.0, "ABEV3": 13.0, "BBSE3": 37.0, "GGBR4": 19.0,
    "SUZB3": 52.0, "PRIO3": 44.0, "ELET3": 41.0, "CMIG4": 12.0, "CPLE6": 10.0,
}


def _number(name: str, default: float) -> float:
    try:
        return float(str(request.args.get(name, default)).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _add_business_days(start: date, amount: int) -> date:
    current, added = start, 0
    while added < amount:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _projected_expiries(today: date) -> list[date]:
    return [today + timedelta(days=days) for days in range(15, 46)
            if (today + timedelta(days=days)).weekday() == 4]


def register(app, legacy):
    def build():
        roots, _profiles = legacy.load_personal_asset_universe(legacy.RADAR_ASSETS)
        tickers = list(dict.fromkeys(roots.values())) or list(REFERENCE_SPOTS)
        selected_asset = str(request.args.get("asset", "")).strip().upper()
        if selected_asset and re.fullmatch(r"[A-Z]{4}[0-9]{1,2}", selected_asset):
            tickers = [selected_asset]
        else:
            selected_asset = ""
        mode = request.args.get("scan_mode", "expiry")
        expiry_options = _projected_expiries(date.today())
        if mode == "business_days":
            business_days = max(1, min(int(_number("business_days", 21)), 32))
            target_expiry = _add_business_days(date.today(), business_days)
        else:
            requested_expiry = str(request.args.get("expiry", ""))
            try:
                parsed_expiry = date.fromisoformat(requested_expiry)
            except ValueError:
                parsed_expiry = None
            target_expiry = parsed_expiry if parsed_expiry in expiry_options else (expiry_options[0] if expiry_options else None)
            business_days = 21
        with ThreadPoolExecutor(max_workers=6) as pool:
            quotes = dict(zip(tickers, pool.map(legacy.cotacao_yahoo, tickers)))
        live_count = sum(bool(value) for value in quotes.values())
        spots = {ticker: float(quotes.get(ticker) or REFERENCE_SPOTS.get(ticker, 0)) for ticker in tickers}
        config = JadeConfig(
            min_liquidity=int(_number("min_liquidity", 1000)),
            min_open_interest=int(_number("min_open_interest", 500)),
            max_spread_pct=_number("max_spread_pct", 15),
            min_score=_number("min_score", 80),
        )
        opportunities = scan_estimated_chain(tickers, spots.get, config, target_expiry=target_expiry)
        search = {"asset": selected_asset, "mode": mode, "business_days": business_days,
                  "expiry": target_expiry.isoformat() if target_expiry else "", "expiry_options": expiry_options}
        return opportunities, config, live_count, len(tickers), search

    @app.get("/estrategias/jade-lizard")
    def radar_jade_lizard():
        opportunities, config, live_count, total, search = build()
        return render_template(
            "radar_jade_lizard.html", opportunities=opportunities, config=config,
            live_count=live_count, total_assets=total, search=search,
            updated_at=datetime.now().strftime("%d/%m/%Y às %H:%M"),
        )

    @app.get("/api/estrategias/jade-lizard")
    def api_radar_jade_lizard():
        opportunities, config, live_count, total, search = build()
        return jsonify({
            "data_mode": "estimated_chain", "live_spots": live_count, "assets": total,
            "filters": config.__dict__, "opportunities": [item.to_dict() for item in opportunities],
            "search": {**search, "expiry_options": [item.isoformat() for item in search["expiry_options"]]},
        })

    @app.post("/api/estrategias/jade-lizard/montar")
    def montar_jade_lizard():
        payload = request.get_json(silent=True) or {}
        required = ("ticker", "put_code", "short_call_code", "long_call_code")
        if any(not payload.get(key) for key in required):
            return jsonify({"ok": False, "error": "Estrutura incompleta."}), 400
        return jsonify({
            "ok": True,
            "status": "plano_pronto",
            "message": "Plano de montagem preparado. Confirme as três pernas na corretora antes de cadastrar a execução.",
            "legs": [
                {"side": "VENDER", "code": payload["put_code"]},
                {"side": "VENDER", "code": payload["short_call_code"]},
                {"side": "COMPRAR", "code": payload["long_call_code"]},
            ],
        })
