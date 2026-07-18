"""Página e API da carteira de ações usada nas CALLs cobertas."""
from decimal import Decimal
from flask import jsonify, redirect, render_template, request, url_for
from services.brokerage_note_service import BrokerageNoteError, note_to_api, parse_btg_necton_pdf, save_imported_note
from services.equity_position_service import portfolio, save_equity_lot


def register(app, legacy):
    def rows():
        values = portfolio(legacy)
        for item in values:
            quote = legacy.cotacao_yahoo(item["asset"])
            item["current_price"] = float(quote) if quote else None
            item["market_value"] = float(quote) * item["quantity"] if quote else None
            item["unrealized_result"] = item["market_value"] - item["cash_cost_total"] if quote else None
            item["logo_url"] = f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{item['asset']}.png"
        return values

    @app.get("/carteira-acoes")
    def equity_portfolio():
        holdings = rows()
        totals = {
            "quantity": sum(item["quantity"] for item in holdings),
            "covered": sum(item["covered_quantity"] for item in holdings),
            "available": sum(item["available_quantity"] for item in holdings),
            "cost": sum(item["cash_cost_total"] for item in holdings),
        }
        return render_template("carteira_acoes.html", holdings=holdings, totals=totals)

    # Mantém endereços antigos e o item histórico do menu apontando para a
    # carteira real, sem apagar o simulador do código legado.
    def legacy_wallet_redirect():
        return redirect(url_for("equity_portfolio"))
    app.view_functions["carteira"] = legacy_wallet_redirect

    @app.post("/api/carteira-acoes/importar-nota")
    def import_equity_note():
        uploaded = request.files.get("brokerage_note")
        if uploaded is None or not uploaded.filename:
            return jsonify({"ok": False, "error": "Selecione uma nota em PDF."}), 400
        try:
            note = parse_btg_necton_pdf(uploaded.read())
            payload = note_to_api(note)
            purchases = [trade for trade in payload["trades"] if trade.get("event_type") == "equity_purchase" and str(trade.get("side", "")).lower() == "compra"]
            if not purchases:
                raise BrokerageNoteError("A nota não possui compra de ações reconhecida. Exercícios de PUT são cadastrados automaticamente no encerramento da opção.")
            imported = []
            for trade in purchases:
                trade_payload = {**payload, "trade": trade}
                lot_id = f"purchase:{payload['document_hash']}:{trade['trade_index']}"
                gross = Decimal(str(trade["gross_value"]))
                costs = Decimal(str(trade["allocated_costs"])) + Decimal(str(trade["allocated_irrf"]))
                quantity = int(trade["quantity"])
                lot = {
                    "lot_id": lot_id, "asset": trade["underlying_asset"], "quantity": quantity,
                    "available_quantity": quantity, "acquisition_date": payload["trade_date"],
                    "exercise_price": str(trade["unit_price"]), "exercise_total": str(gross),
                    "exercise_costs": str(costs), "cash_cost_total": str(gross + costs),
                    "option_premium_gross": "0", "option_opening_costs": "0",
                    "tax_cost_total": str(gross + costs),
                    "tax_cost_per_share": str((gross + costs) / Decimal(quantity)),
                    "source": "Compra de ações por nota", "source_operation_id": "",
                    "source_option": "", "source_note_key": f"{payload['document_hash']}:{trade['trade_index']}",
                }
                if not save_imported_note(legacy, trade_payload, f"equity:{trade['underlying_asset']}"):
                    raise BrokerageNoteError(f"A compra de {trade['underlying_asset']} desta nota já foi importada.")
                if not save_equity_lot(legacy, lot):
                    raise BrokerageNoteError(f"O lote de {trade['underlying_asset']} já foi cadastrado.")
                imported.append(trade["underlying_asset"])
            return jsonify({"ok": True, "imported": imported, "message": "Ações incluídas na Carteira com custo médio recalculado."})
        except BrokerageNoteError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/carteira-acoes")
    def equity_portfolio_api():
        return jsonify({"ok": True, "holdings": rows()})
