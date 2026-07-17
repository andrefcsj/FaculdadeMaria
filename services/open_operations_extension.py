"""Integra probabilidade de exercício e edição em modal na tela de operações abertas."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

from flask import jsonify, redirect, render_template, request, url_for

from services.exercise_probability_service import estimate_operation_exercise_probability
from services.dashboard_market_service import load_option_quotes
from services.manual_option_quote_service import save_manual_option_quote
from services.operation_preferences_service import load_operation_metadata, normalize_exercise_interest, operation_underlying, save_operation_metadata
from services.equity_position_service import portfolio as equity_portfolio, validate_covered_call


def register(app, legacy):
    def prepare(operation, option_quotes):
        ticker = operation_underlying(legacy, operation)
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
        expiry_status = None
        expiry_status_class = "waiting"
        if expiry and expiry <= date.today():
            if not spot or not strike:
                expiry_status = "Aguardando fechamento da B3"
            elif (str(operation.get("Tipo", "PUT")).upper() == "PUT" and spot < strike) or (str(operation.get("Tipo", "PUT")).upper() == "CALL" and spot > strike):
                expiry_status, expiry_status_class = "Exercício provável", "exercise"
            else:
                expiry_status, expiry_status_class = "Expira sem valor", "expires"
        operation["expiry_status"] = expiry_status
        operation["expiry_status_class"] = expiry_status_class
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
        option_capital = sum(legacy.fnum(operation.get("Capital"), 0) for operation in abertas)
        equity_capital = sum(float(item.get("cash_cost_total", 0)) for item in equity_portfolio(legacy, ops))
        total_capital = option_capital + equity_capital
        total_result = sum(legacy.fnum(operation.get("Fluxo_liquido"), 0) for operation in abertas)
        open_totals = {
            "capital": total_capital,
            "result": total_result,
            "roi": total_result / total_capital * 100 if total_capital else 0,
            "equity_capital": equity_capital,
        }
        return render_template("operacoes_abertas.html", abertas=abertas, ops=ops, fechadas=fechadas, cfg=cfg, ind=legacy.metrics(ops, fechadas, cfg), open_totals=open_totals)

    app.view_functions["operacoes_abertas"] = view

    def raw_operation(operation_id):
        rows = legacy.read_csv(legacy.OPERACOES)
        operation = legacy.get_operacao_pg(operation_id) if legacy.USE_POSTGRES else legacy.find_row(rows, operation_id)
        return rows, operation

    def serialize(operation):
        option_code = str(operation.get("Ativo", ""))
        preferences = load_operation_metadata(legacy)
        metadata = preferences.get(str(operation.get("ID", "")), {})
        enriched_operation = dict(operation)
        if metadata.get("underlying_asset"):
            enriched_operation["Ativo_subjacente"] = metadata["underlying_asset"]
        underlying = operation_underlying(legacy, enriched_operation)
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
            "Interesse_exercicio": metadata.get("exercise_interest", False),
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
        raw_strategy = str(payload.get("Estrategia", current.get("Estratégia", "Venda"))).strip().lower()
        strategy = {"venda": "Venda", "compra": "Compra", "venda coberta": "Venda Coberta", "call coberta": "Venda Coberta"}.get(raw_strategy)
        if not strategy:
            raise ValueError("Estratégia inválida.")
        current.update({
            "Ativo": str(payload.get("Ativo", current.get("Ativo", ""))).strip().upper(),
            "Tipo": option_type,
            "Estratégia": strategy,
            "Status": status,
            "Vencimento": expiry,
            **values,
        })
        if not current["Ativo"]:
            raise ValueError("Código da opção é obrigatório.")
        if strategy == "Venda Coberta":
            if option_type != "CALL":
                raise ValueError("Venda coberta deve ser uma CALL.")
            underlying = str(payload.get("Ativo_subjacente") or operation_underlying(legacy, current)).upper()
            validate_covered_call(legacy, underlying, Decimal(values["Contratos"]), exclude_operation_id=str(current.get("ID", "")))
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
            save_operation_metadata(
                legacy, operation_id,
                interested=normalize_exercise_interest(payload.get("Interesse_exercicio", False)),
                underlying_asset=payload.get("Ativo_subjacente", updated.get("Ativo_subjacente", "")),
            )
            return jsonify({"ok": True, "operation": serialize(updated)})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/operacoes/<operation_id>/preco-atual")
    def save_current_option_price(operation_id):
        _rows, operation = raw_operation(operation_id)
        if operation is None:
            return jsonify({"ok": False, "error": "Operação não encontrada."}), 404
        try:
            payload = request.get_json(silent=True) or {}
            record = save_manual_option_quote(
                legacy, operation.get("Ativo", ""), payload.get("price"), payload.get("quoted_at")
            )
            return jsonify({"ok": True, "quote": record, "message": "Preço do ProfitPro atualizado."})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    def editar_descontinuado(oid):
        return redirect(url_for("operacoes_abertas"))

    app.view_functions["editar"] = editar_descontinuado
