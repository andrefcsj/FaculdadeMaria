"""Ponto de entrada do FaculdadeMaria com extensão de importação de mercado."""
from __future__ import annotations

import json
from decimal import Decimal

import legacy_app as legacy
from flask import redirect, render_template, request, url_for

from engine.providers import apply_intraday_quote
from services.market_import_service import (
    MarketImportError,
    load_market_import,
    parse_market_csv,
    save_market_import,
)
from services.radar_service import build_radar_from_market

app = legacy.app
RADAR_IMPORTED = legacy.DATA / "market" / "imported_options.json"
_original_radar_view = app.view_functions["radar_oportunidades"]


def _load_profiles():
    roots, profiles = legacy.load_personal_asset_universe(legacy.RADAR_ASSETS)
    if legacy.RADAR_DFP.exists():
        issuer_config = legacy.load_cvm_issuer_config(legacy.RADAR_ASSETS)
        profiles = legacy.CvmFundamentalsProvider(legacy.RADAR_DFP, issuer_config).fetch()
    return roots, profiles


def radar_oportunidades_importado():
    imported = load_market_import(RADAR_IMPORTED)
    if imported is None:
        return _original_radar_view()

    cards = ()
    message = request.args.get("message", "")
    try:
        _, profiles = _load_profiles()
        opportunities = list(imported.opportunities)
        overrides = (
            json.loads(legacy.RADAR_QUOTES.read_text(encoding="utf-8"))
            if legacy.RADAR_QUOTES.exists()
            else {}
        )
        for index, opportunity in enumerate(opportunities):
            quote = overrides.get(opportunity.option_code)
            if quote:
                opportunities[index] = apply_intraday_quote(
                    opportunity,
                    premium=Decimal(str(quote["premium"])),
                    bid=Decimal(str(quote["bid"])) if quote.get("bid") not in (None, "") else None,
                    ask=Decimal(str(quote["ask"])) if quote.get("ask") not in (None, "") else None,
                )
        cards = build_radar_from_market(opportunities, profiles)[:50]
    except Exception as exc:
        message = f"Não foi possível processar o mercado importado: {exc}"

    return render_template(
        "radar_oportunidades.html",
        cards=cards,
        message=message,
        has_eod=True,
        has_quality=legacy.RADAR_DFP.exists(),
        last_import_at=imported.imported_at.strftime("%d/%m/%Y às %H:%M"),
        imported_rows=imported.accepted_rows,
    )


app.view_functions["radar_oportunidades"] = radar_oportunidades_importado


@app.route("/radar-oportunidades/importar-mercado", methods=["POST"])
def importar_mercado():
    uploaded = request.files.get("market_file")
    if uploaded is None or not uploaded.filename:
        return redirect(url_for("radar_oportunidades", message="Selecione um arquivo CSV."))
    if not uploaded.filename.lower().endswith(".csv"):
        return redirect(url_for("radar_oportunidades", message="Nesta Sprint, envie um arquivo .CSV."))
    data = uploaded.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return redirect(url_for("radar_oportunidades", message="O CSV deve ter no máximo 5 MB."))
    try:
        result = parse_market_csv(data)
        save_market_import(RADAR_IMPORTED, result)
        message = (
            f"Mercado importado: {result.accepted_rows} PUTs válidas"
            f" e {result.rejected_rows} linhas ignoradas."
        )
    except MarketImportError as exc:
        message = f"Não foi possível importar o CSV: {exc}"
    except Exception as exc:
        message = f"Falha inesperada na importação: {exc}"
    return redirect(url_for("radar_oportunidades", message=message))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
