"""Ponto de entrada do FaculdadeMaria com extensões funcionais Premium."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal

import legacy_app as legacy
from flask import jsonify, redirect, render_template, request, url_for

from engine.providers import apply_intraday_quote
from engine.roll import RollInput, analyze_put_roll
from services.exercise_probability_service import estimate_operation_exercise_probability
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


def _prepare_open_operation(operation):
    ticker = legacy.infer_acao_from_option(operation.get("Ativo", ""))
    expiry = legacy.parse_date(str(operation.get("Vencimento", "")))
    estimate = estimate_operation_exercise_probability(
        ticker=ticker,
        option_type=str(operation.get("Tipo", "PUT")),
        strike=Decimal(str(legacy.fnum(operation.get("Strike")))),
        expiry=expiry,
    )
    operation["ticker"] = ticker
    operation["cotacao_atual"] = float(estimate.spot_price) if estimate.spot_price is not None else legacy.fnum(operation.get("Cotacao_atual"), 0) or None
    operation["logo_url"] = f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png" if ticker else None
    operation["exercise_probability"] = estimate.percentage
    operation["exercise_probability_label"] = estimate.label
    operation["exercise_probability_class"] = (
        "high" if estimate.probability is not None and estimate.probability >= Decimal("0.65")
        else "mid" if estimate.probability is not None and estimate.probability >= Decimal("0.35")
        else "low" if estimate.probability is not None
        else "unavailable"
    )
    volatility_text = f" Volatilidade histórica: {(estimate.annual_volatility * Decimal('100')).quantize(Decimal('0.1'))}%." if estimate.annual_volatility is not None else ""
    operation["exercise_probability_tooltip"] = f"{estimate.methodology}{volatility_text}"
    return operation


def operacoes_abertas_premium():
    ops, fechadas, cfg = legacy.load_all()
    abertas = [operation for operation in ops if str(operation.get("Status", "")).lower() == "aberta"]
    if abertas:
        with ThreadPoolExecutor(max_workers=min(6, len(abertas))) as executor:
            abertas = list(executor.map(_prepare_open_operation, abertas))
    return render_template(
        "operacoes_abertas.html",
        abertas=abertas,
        ops=ops,
        fechadas=fechadas,
        cfg=cfg,
        ind=legacy.metrics(ops, fechadas, cfg),
    )


app.view_functions["operacoes_abertas"] = operacoes_abertas_premium


def _raw_operation(operation_id: str):
    rows = legacy.read_csv(legacy.OPERACOES)
    operation = legacy.get_operacao_pg(operation_id) if legacy.USE_POSTGRES else legacy.find_row(rows, operation_id)
    return rows, operation


def _serialize_operation(operation):
    return {
        "ID": str(operation.get("ID", "")),
        "Ativo": str(operation.get("Ativo", "")),
        "Tipo": str(operation.get("Tipo", "PUT")),
        "Estrategia": str(operation.get("Estratégia", "Venda")),
        "Status": str(operation.get("Status", "Aberta")),
        "Contratos": str(operation.get("Contratos", "1")),
        "Strike": str(operation.get("Strike", "0")),
        "Premio_opcao": str(operation.get("Premio_opcao", "0")),
        "Custos": str(operation.get("Custos", "0")),
        "IRRF": str(operation.get("IRRF", "0")),
        "Vencimento": str(operation.get("Vencimento", "")),
        "Cotacao_atual": str(operation.get("Cotacao_atual", "0")),
    }


def _validated_operation_payload(payload, current):
    option_type = str(payload.get("Tipo", current.get("Tipo", "PUT"))).upper()
    if option_type not in {"PUT", "CALL"}:
        raise ValueError("Tipo de opção inválido.")
    status = str(payload.get("Status", current.get("Status", "Aberta"))).capitalize()
    if status not in {"Aberta", "Encerrada"}:
        raise ValueError("Status inválido.")
    values = {}
    for field in ("Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Cotacao_atual"):
        raw = str(payload.get(field, current.get(field, "0"))).strip().replace("R$", "").replace(" ", "")
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        parsed = Decimal(raw or "0")
        if parsed < 0:
            raise ValueError(f"{field} não pode ser negativo.")
        values[field] = str(parsed)
    expiry = str(payload.get("Vencimento", current.get("Vencimento", ""))).strip()
    if legacy.parse_date(expiry) is None:
        raise ValueError("Vencimento inválido.")
    current.update({
        "Ativo": str(payload.get("Ativo", current.get("Ativo", ""))).strip().upper(),
        "Tipo": option_type,
        "Estratégia": str(payload.get("Estrategia", current.get("Estratégia", "Venda"))).strip(),
        "Status": status,
        "Vencimento": expiry,
        **values,
    })
    if not current["Ativo"]:
        raise ValueError("Código da opção é obrigatório.")
    return current


@app.route("/api/operacoes/<operation_id>", methods=["GET", "POST"])
def api_operacao(operation_id: str):
    rows, operation = _raw_operation(operation_id)
    if operation is None:
        return jsonify({"ok": False, "error": "Operação não encontrada."}), 404
    if request.method == "GET":
        return jsonify({"ok": True, "operation": _serialize_operation(operation)})
    try:
        updated = _validated_operation_payload(request.get_json(silent=True) or {}, operation)
        if legacy.USE_POSTGRES:
            connection = legacy.get_pg_conn()
            cursor = connection.cursor()
            cursor.execute(
                """UPDATE operacoes SET ativo=%s,tipo=%s,estrategia=%s,status=%s,contratos=%s,
                   strike=%s,premio_opcao=%s,custos=%s,irrf=%s,vencimento=%s,cotacao_atual=%s WHERE id=%s""",
                (
                    updated["Ativo"], updated["Tipo"], updated["Estratégia"], updated["Status"],
                    updated["Contratos"], updated["Strike"], updated["Premio_opcao"], updated["Custos"],
                    updated["IRRF"], updated["Vencimento"], updated["Cotacao_atual"], operation_id,
                ),
            )
            connection.commit()
            connection.close()
        else:
            legacy.write_csv(
                legacy.OPERACOES,
                rows,
                ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"],
            )
        return jsonify({"ok": True, "operation": _serialize_operation(updated)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


def editar_descontinuado(oid: str):
    return redirect(url_for("operacoes_abertas"))


app.view_functions["editar"] = editar_descontinuado


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
