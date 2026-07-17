"""Página e API da carteira de ações usada nas CALLs cobertas."""
from flask import jsonify, render_template
from services.equity_position_service import portfolio


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

    @app.get("/api/carteira-acoes")
    def equity_portfolio_api():
        return jsonify({"ok": True, "holdings": rows()})
