"""Página independente para comparação de CALLs cobertas."""
from __future__ import annotations

from flask import jsonify, render_template, request

from services.sldx_market_service import SldxMarketError, fetch_option_chain


def register(app, _legacy):
    @app.get("/estrategias/comparador-call-coberta")
    def comparador_call_coberta():
        return render_template("comparador_call_coberta.html")

    @app.get("/api/comparador-call-coberta/opcao")
    def consultar_call_coberta():
        asset = request.args.get("ativo", "").upper().strip().removesuffix(".SA")
        code = request.args.get("codigo", "").upper().strip().removesuffix(".SA")
        if not asset or not code:
            return jsonify({"ok": False, "message": "Informe o ativo e o código da CALL."}), 400
        option_type = request.args.get("tipo", "CALL").upper().strip()
        if option_type not in {"CALL", "PUT"}:
            return jsonify({"ok": False, "message": "Tipo de opção inválido."}), 400
        try:
            options = fetch_option_chain(asset, option_types=(option_type,), timeout=8)
        except SldxMarketError as exc:
            return jsonify({"ok": False, "message": str(exc)}), 502
        option = next((item for item in options if item.option_code.removesuffix(".SA") == code), None)
        if option is None:
            return jsonify({"ok": False, "message": f"{option_type} não encontrada para este ativo."}), 404
        return jsonify({"ok": True, "option": {"code": option.option_code, "strike": float(option.strike), "premium": float(option.premium), "expiry": option.expiry.isoformat(), "spot": float(option.spot_price), "source": "SLDX"}})
