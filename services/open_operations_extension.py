"""Integra probabilidade de exercício e edição em modal na tela de operações abertas."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from flask import jsonify, redirect, render_template, request, url_for

from services.exercise_probability_service import estimate_operation_exercise_probability
from services.dashboard_market_service import load_option_quotes
from services.operation_preferences_service import load_operation_preferences, normalize_exercise_interest, save_exercise_interest


def register(app, legacy):
    def prepare(operation, option_quotes):
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
        quote = option_quotes.get(str(operation.get("Ativo", "")).upper(), {})
        operation["preco_venda"] = legacy.fnum(operation.get("Premio_opcao"), 0)
        operation["preco_atual_opcao"] = float(quote["price"]) if quote.get("price") is not None else None
        operation["fonte_preco_atual"] = str(quote.get("source", "Cotação da opção indisponível"))
        strike = legacy.fnum(operation.get("Strike"), 0)
        spot = operation["cotacao_atual"] or 0
        operation["distancia_strike"] = ((spot - strike) / strike * 100) if spot and strike else None
        operation["distancia_strike_class"] = "positive" if operation["distancia_strike"] is not None and operation["distancia_strike"] >= 0 else "negative" if operation["distancia_strike"] is not None else "unavailable"
        operation["logo_url"] = f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png" if ticker else None
        operation["exercise_probability"] = estimate.percentage
        operation["exercise_probability_label"] = estimate.label
        operation["exercise_probability_class"] = "high" if estimate.probability is not None and estimate.probability >= Decimal("0.65") else "mid" if estimate.probability is not None and estimate.probability >= Decimal("0.35") else "low" if estimate.probability is not None else "unavailable"
        vol = f" Volatilidade histórica: {(estimate.annual_volatility * Decimal('100')).quantize(Decimal('0.1'))}%." if estimate.annual_volatility is not None else ""
        operation["exercise_probability_tooltip"] = f"{estimate.methodology}{vol}"
        return operation

    def view():
        ops, fechadas, cfg = legacy.load_all()
        abertas = [o for o in ops if str(o.get("Status", "")).lower() == "aberta"]
        if abertas:
            option_quotes = load_option_quotes(legacy)
            with ThreadPoolExecutor(max_workers=min(6, len(abertas))) as executor:
                abertas = list(executor.map(lambda operation: prepare(operation, option_quotes), abertas))
        return render_template("operacoes_abertas.html", abertas=abertas, ops=ops, fechadas=fechadas, cfg=cfg, ind=legacy.metrics(ops, fechadas, cfg))

    app.view_functions["operacoes_abertas"] = view

    def raw_operation(operation_id):
        rows = legacy.read_csv(legacy.OPERACOES)
        operation = legacy.get_operacao_pg(operation_id) if legacy.USE_POSTGRES else legacy.find_row(rows, operation_id)
        return rows, operation

    def serialize(operation):
        option_code = str(operation.get("Ativo", ""))
        underlying = legacy.infer_acao_from_option(option_code)
        preferences = load_operation_preferences(legacy)
        return {
            "ID": str(operation.get("ID", "")),
            "Ativo": option_code,
            "Ativo_subjacente": underlying,
            "Logo_subjacente": f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{underlying}.png" if underlying else "",
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
            "Interesse_exercicio": preferences.get(str(operation.get("ID", "")), False),
        }

    def validate(payload, current):
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
    def api_operacao(operation_id):
        rows, operation = raw_operation(operation_id)
        if operation is None:
            return jsonify({"ok": False, "error": "Operação não encontrada."}), 404
        if request.method == "GET":
            return jsonify({"ok": True, "operation": serialize(operation)})
        try:
            payload = request.get_json(silent=True) or {}
            updated = validate(payload, operation)
            if legacy.USE_POSTGRES:
                connection = legacy.get_pg_conn()
                cursor = connection.cursor()
                cursor.execute(
                    """UPDATE operacoes SET ativo=%s,tipo=%s,estrategia=%s,status=%s,contratos=%s,strike=%s,premio_opcao=%s,custos=%s,irrf=%s,vencimento=%s,cotacao_atual=%s WHERE id=%s""",
                    (updated["Ativo"], updated["Tipo"], updated["Estratégia"], updated["Status"], updated["Contratos"], updated["Strike"], updated["Premio_opcao"], updated["Custos"], updated["IRRF"], updated["Vencimento"], updated["Cotacao_atual"], operation_id),
                )
                connection.commit()
                connection.close()
            else:
                legacy.write_csv(legacy.OPERACOES, rows, ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"])
            save_exercise_interest(legacy, operation_id, normalize_exercise_interest(payload.get("Interesse_exercicio", False)))
            return jsonify({"ok": True, "operation": serialize(updated)})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    def editar_descontinuado(oid):
        return redirect(url_for("operacoes_abertas"))

    app.view_functions["editar"] = editar_descontinuado
