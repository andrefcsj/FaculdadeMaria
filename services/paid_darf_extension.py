"""Rotas da central de DARFs pagos."""
from __future__ import annotations
from datetime import date
from flask import jsonify,render_template,request
from services.cash_ledger_service import money
from services.paid_darf_service import build_darf_dashboard,delete_paid_darf,save_paid_darf
def register(app,legacy):
    @app.get("/darfs-pagos")
    def paid_darfs():
        scope=request.args.get("periodo","all");scope=scope if scope in {"all","month","year"} else "all";return render_template("darfs_pagos.html",darf_dashboard=build_darf_dashboard(legacy,scope=scope,month=request.args.get("mes",""),year=request.args.get("ano","")))
    @app.post("/api/darfs-pagos")
    def add_paid_darf():
        try:
            uploaded=request.files.get("pdf");pdf=uploaded.read() if uploaded and uploaded.filename else None;payment=legacy.parse_date(request.form.get("payment_date","")) or date.today();due=legacy.parse_date(request.form.get("due_date",""));record=save_paid_darf(legacy,competence=request.form.get("competence",""),payment_date=payment,due_date=due,revenue_code=request.form.get("revenue_code","6015"),amount=money(request.form.get("amount")),description=request.form.get("description",""),pdf=pdf);return jsonify({"ok":True,"record":record})
        except Exception as exc:return jsonify({"ok":False,"error":str(exc)}),400
    @app.delete("/api/darfs-pagos/<darf_id>")
    def remove_paid_darf(darf_id):
        if not delete_paid_darf(legacy,darf_id):return jsonify({"ok":False,"error":"DARF não encontrado."}),404
        return jsonify({"ok":True})
