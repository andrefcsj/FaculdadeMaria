"""Ponto de entrada do FaculdadeMaria com importação de mercado e rolagem inteligente."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import legacy_app as legacy
from flask import redirect, render_template, request, url_for

from engine.providers import apply_intraday_quote
from engine.roll import RollInput, analyze_put_roll
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
        overrides = json.loads(legacy.RADAR_QUOTES.read_text(encoding="utf-8")) if legacy.RADAR_QUOTES.exists() else {}
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
        "radar_oportunidades.html", cards=cards, message=message, has_eod=True,
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
        message = f"Mercado importado: {result.accepted_rows} PUTs válidas e {result.rejected_rows} linhas ignoradas."
    except MarketImportError as exc:
        message = f"Não foi possível importar o CSV: {exc}"
    except Exception as exc:
        message = f"Falha inesperada na importação: {exc}"
    return redirect(url_for("radar_oportunidades", message=message))


def _open_puts():
    rows = legacy.read_operacoes()
    return [row for row in rows if str(row.get("Status", "")).lower() == "aberta" and str(row.get("Tipo", "PUT")).upper() == "PUT"]


def _selected_operation(rows, operation_id: str):
    return next((row for row in rows if str(row.get("ID", "")) == str(operation_id)), None)


def _decimal_form(name: str) -> Decimal:
    value = request.form.get(name, "").strip().replace("R$", "").replace(" ", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return Decimal(value)


@app.route("/rolagem-inteligente", methods=["GET", "POST"])
def rolagem_inteligente():
    operations = _open_puts()
    analysis = None
    error = ""
    selected = None
    if request.method == "POST":
        try:
            selected = _selected_operation(operations, request.form.get("operation_id", ""))
            if selected is None:
                raise ValueError("Selecione uma PUT aberta válida.")
            current_expiry = legacy.parse_date(str(selected.get("Vencimento", "")))
            if current_expiry is None:
                raise ValueError("A operação atual não possui vencimento válido.")
            data = RollInput(
                option_code=str(selected.get("Ativo", "")).upper(),
                current_strike=Decimal(str(legacy.fnum(selected.get("Strike")))),
                original_premium=Decimal(str(legacy.fnum(selected.get("Premio_opcao")))),
                current_expiry=current_expiry,
                buyback_price=_decimal_form("buyback_price"),
                new_option_code=request.form.get("new_option_code", "").strip().upper(),
                new_strike=_decimal_form("new_strike"),
                new_premium=_decimal_form("new_premium"),
                new_expiry=datetime.strptime(request.form.get("new_expiry", ""), "%Y-%m-%d").date(),
                spot_price=_decimal_form("spot_price"),
                contract_size=int(legacy.fnum(request.form.get("contract_size"), 100)),
                costs_total=_decimal_form("costs_total") if request.form.get("costs_total", "").strip() else Decimal("0"),
            )
            analysis = analyze_put_roll(data)
        except Exception as exc:
            error = str(exc)
    return render_template("rolagem_inteligente.html", operations=operations, analysis=analysis, error=error, selected=selected)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
