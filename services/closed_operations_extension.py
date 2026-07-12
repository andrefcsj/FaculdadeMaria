"""Página Premium e APIs seguras para operações fechadas."""
from __future__ import annotations

from flask import jsonify, redirect, render_template, request, url_for

from services.closed_operations_service import (
    _decimal, build_closed_dashboard, delete_closure_metadata, delete_operation,
    load_closure_metadata, persist_operation, raw_operation, save_closure_metadata,
    serialize_closed_operation,
)


def register(app, legacy):
    def closed_view():
        scope = request.args.get("periodo", "all")
        if scope not in {"current", "year", "month", "all"}: scope = "all"
        dashboard = build_closed_dashboard(legacy, scope=scope, selected_month=request.args.get("mes", ""))
        return render_template("operacoes_fechadas.html", closed_dashboard=dashboard)

    app.view_functions["op_fechadas"] = closed_view

    @app.get("/operacoes-fechadas")
    def closed_operations_alias():
        return closed_view()

    @app.route("/api/operacoes-fechadas/<operation_id>", methods=["GET", "POST", "DELETE"])
    def closed_operation_api(operation_id):
        rows, operation = raw_operation(legacy, operation_id)
        if operation is None or str(operation.get("Status", "")).lower() != "encerrada":
            return jsonify({"ok": False, "error": "Operação fechada não encontrada."}), 404
        metadata = load_closure_metadata(legacy).get(str(operation_id), {})
        if request.method == "GET":
            return jsonify({"ok": True, "operation": serialize_closed_operation(legacy, operation, metadata)})
        if request.method == "DELETE":
            delete_operation(legacy, rows, operation_id); delete_closure_metadata(legacy, operation_id)
            return jsonify({"ok": True, "message": "Operação excluída."})
        try:
            payload = request.get_json(silent=True) or {}
            for field in ("Ativo", "Tipo", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"):
                if field in payload: operation[field] = str(payload[field]).strip()
            operation["Estratégia"] = str(payload.get("Estrategia", operation.get("Estratégia", "Venda")))
            operation["Status"] = "Encerrada"
            if not operation.get("Ativo") or legacy.parse_date(str(operation.get("Vencimento", ""))) is None:
                raise ValueError("Código e vencimento válidos são obrigatórios.")
            for field in ("Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Cotacao_atual"):
                if _decimal(operation.get(field)) < 0: raise ValueError(f"{field} não pode ser negativo.")
            close_date = legacy.parse_date(str(payload.get("Data_fechamento", metadata.get("close_date", ""))))
            if close_date is None: raise ValueError("Informe a data de fechamento.")
            persist_operation(legacy, rows, operation)
            save_closure_metadata(legacy, operation_id, close_date=close_date, method=str(payload.get("Metodo_encerramento", metadata.get("method", "editado"))), repurchase_value=_decimal(payload.get("Valor_recompra", metadata.get("repurchase_value", "0"))), result=_decimal(operation.get("Resultado_realizado")))
            return jsonify({"ok": True, "operation": serialize_closed_operation(legacy, operation, load_closure_metadata(legacy).get(str(operation_id)))})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/operacoes-fechadas/<operation_id>/reabrir")
    def reopen_closed_operation(operation_id):
        rows, operation = raw_operation(legacy, operation_id)
        if operation is None or str(operation.get("Status", "")).lower() != "encerrada":
            return jsonify({"ok": False, "error": "Operação fechada não encontrada."}), 404
        operation["Status"] = "Aberta"; operation["Resultado_realizado"] = "0"
        persist_operation(legacy, rows, operation); delete_closure_metadata(legacy, operation_id)
        return jsonify({"ok": True, "redirect": url_for("operacoes_abertas"), "message": "Operação reaberta e cálculos atualizados."})
