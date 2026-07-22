"""Página e API da carteira de ações usada nas CALLs cobertas."""
from datetime import date
from decimal import Decimal
from flask import jsonify, redirect, render_template, request, url_for
from services.brokerage_note_service import BrokerageNoteError, note_to_api, parse_btg_necton_pdf, save_imported_note
from services.cash_ledger_service import money, save_cash_event
from services.equity_position_service import (
    delete_equity_asset, manual_equity_lot, portfolio, replace_equity_asset,
    save_equity_lot, sell_equity_asset,
)


def register(app, legacy):
    def rows():
        values = portfolio(legacy)
        for item in values:
            quote = legacy.cotacao_yahoo(item["asset"])
            item["current_price"] = float(quote) if quote else None
            item["market_value"] = float(quote) * item["quantity"] if quote else None
            item["unrealized_result"] = item["market_value"] - item["cash_cost_total"] if quote else None
            item["appreciation"] = ((float(quote) / item["tax_cost_per_share"] - 1) * 100) if quote and item["tax_cost_per_share"] else None
            item["appreciation_class"] = "positive" if item["appreciation"] is not None and item["appreciation"] >= 0 else "negative" if item["appreciation"] is not None else "unavailable"
            item["total_allocated"] = item["tax_cost_per_share"] * item["quantity"]
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
                    "note_pending": bool(payload.get("is_provisional", False)),
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

    @app.post("/api/carteira-acoes/manual")
    def add_manual_equity():
        try:
            payload = request.get_json(silent=True) or {}
            quantity = int(payload.get("quantity", 0))
            average_price = money(payload.get("average_price"))
            acquisition = legacy.parse_date(str(payload.get("acquisition_date", ""))) or date.today()
            lot = manual_equity_lot(asset=payload.get("asset", ""), quantity=quantity, average_price=average_price, acquisition_date=acquisition.isoformat())
            if not save_equity_lot(legacy, lot):
                raise ValueError("Não foi possível incluir a ação.")
            return jsonify({"ok": True, "message": "Ação adicionada à carteira para simulação."})
        except (ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.put("/api/carteira-acoes/<asset>")
    def edit_equity(asset: str):
        try:
            payload = request.get_json(silent=True) or {}
            acquisition = legacy.parse_date(str(payload.get("acquisition_date", ""))) or date.today()
            replace_equity_asset(
                legacy, asset=asset, quantity=int(payload.get("quantity", 0)),
                average_price=money(payload.get("average_price")), acquisition_date=acquisition.isoformat(),
            )
            return jsonify({"ok": True, "message": "Posição atualizada e totais recalculados."})
        except (ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.delete("/api/carteira-acoes/<asset>")
    def delete_equity(asset: str):
        try:
            if not delete_equity_asset(legacy, asset):
                return jsonify({"ok": False, "error": "Ação não encontrada."}), 404
            return jsonify({"ok": True, "message": "Ação excluída e carteira recalculada."})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/carteira-acoes/<asset>/vender")
    def sell_equity(asset: str):
        try:
            payload = request.get_json(silent=True) or {}
            quantity = int(payload.get("quantity", 0))
            sale_price = money(payload.get("sale_price"))
            if sale_price <= 0:
                raise ValueError("O preço de venda deve ser maior que zero.")
            sale_date = legacy.parse_date(str(payload.get("sale_date", ""))) or date.today()
            sell_equity_asset(legacy, asset=asset, quantity=quantity)
            save_cash_event(
                legacy, kind="venda_acoes", amount=sale_price * Decimal(quantity),
                event_date=sale_date, description=f"Venda de {quantity} ações {asset.upper()}",
            )
            return jsonify({"ok": True, "message": "Venda registrada, ações baixadas e saldo recalculado."})
        except (ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
