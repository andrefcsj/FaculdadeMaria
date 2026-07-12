"""Central administrativa de limpeza operacional."""
from __future__ import annotations

import hmac
import os
from datetime import date

from flask import jsonify, render_template, request

from services.system_cleanup_service import execute_cleanup, expected_confirmation, preview_cleanup


def register(app, legacy):
    def settings_view():
        operations, closed, config = legacy.load_all()
        return render_template("configuracoes.html", cfg=config, cleanup_enabled=bool(os.getenv("ADMIN_RESET_PIN")), operational_counts={"operations":len(operations),"closed":sum(1 for row in operations if str(row.get("Status","")).lower()=="encerrada")}, now_month=date.today().strftime("%Y-%m"))
    app.view_functions["configuracoes"] = settings_view

    def valid_scope(payload):
        scope = str(payload.get("scope", ""))
        period = str(payload.get("period", ""))
        if scope not in {"month","year","all"}: raise ValueError("Escopo inválido.")
        if scope == "month":
            if len(period)!=7 or period[4]!="-": raise ValueError("Mês inválido.")
        elif scope == "year":
            if len(period)!=4 or not period.isdigit(): raise ValueError("Ano inválido.")
        else: period=""
        return scope,period

    @app.post("/api/configuracoes/limpeza/preview")
    def cleanup_preview():
        try:
            scope, period = valid_scope(request.get_json(silent=True) or {})
            preview = preview_cleanup(legacy,scope=scope,period=period)
            return jsonify({"ok":True,"preview":{"operations":preview.operations,"notes":preview.imported_notes,"closures":preview.closures,"legacy":preview.legacy_closed,"cash_events":preview.cash_events,"paid_darfs":preview.paid_darfs,"total":preview.total},"confirmation":expected_confirmation(scope,period),"enabled":bool(os.getenv("ADMIN_RESET_PIN"))})
        except Exception as exc:
            return jsonify({"ok":False,"error":str(exc)}),400

    @app.post("/api/configuracoes/limpeza/executar")
    def cleanup_execute():
        try:
            payload=request.get_json(silent=True) or {}; scope,period=valid_scope(payload)
            configured=os.getenv("ADMIN_RESET_PIN","")
            if not configured: raise ValueError("Configure ADMIN_RESET_PIN no Render antes de usar a limpeza.")
            if not hmac.compare_digest(str(payload.get("pin","")),configured): raise ValueError("Senha administrativa incorreta.")
            if str(payload.get("confirmation","")) != expected_confirmation(scope,period): raise ValueError("Texto de confirmação incorreto.")
            result=execute_cleanup(legacy,scope=scope,period=period)
            return jsonify({"ok":True,"deleted":{"operations":result.operations,"notes":result.imported_notes,"closures":result.closures,"legacy":result.legacy_closed,"cash_events":result.cash_events,"paid_darfs":result.paid_darfs},"message":"Dados operacionais excluídos e indicadores recalculados."})
        except Exception as exc:
            return jsonify({"ok":False,"error":str(exc)}),400
