"""Página e APIs de aportes, retiradas e livro-caixa."""
from __future__ import annotations
from datetime import date
from flask import jsonify,render_template,request
from services.cash_ledger_service import build_cash_dashboard,delete_cash_event,money,save_cash_event

def register(app,legacy):
    @app.get("/novos-aportes")
    def cash_management():return render_template("novos_aportes.html",cash_dashboard=build_cash_dashboard(legacy),now_date=date.today().isoformat())
    @app.post("/api/caixa/movimentos")
    def add_cash_event():
        try:
            payload=request.get_json(silent=True) or {};event_date=legacy.parse_date(str(payload.get("date",""))) or date.today();record=save_cash_event(legacy,kind=str(payload.get("kind","")),amount=money(payload.get("amount")),event_date=event_date,description=str(payload.get("description","")));return jsonify({"ok":True,"event":record,"summary":{"balance":str(build_cash_dashboard(legacy)["balance"])}})
        except Exception as exc:return jsonify({"ok":False,"error":str(exc)}),400
    @app.delete("/api/caixa/movimentos/<event_id>")
    def remove_cash_event(event_id):
        if not delete_cash_event(legacy,event_id):return jsonify({"ok":False,"error":"Movimentação não encontrada."}),404
        return jsonify({"ok":True,"summary":{"balance":str(build_cash_dashboard(legacy)["balance"])}})
