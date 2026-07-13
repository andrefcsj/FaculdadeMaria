"""Rotas de importação e painel de notas BTG/Necton."""
from __future__ import annotations

from flask import jsonify, render_template, request

from services.brokerage_note_service import (
    BrokerageNoteError,
    build_notes_dashboard,
    delete_imported_note,
    load_imported_notes,
    note_to_api,
    parse_btg_necton_pdf,
)


def register(app, legacy):
    def closure_candidate(trade):
        if str(trade.get("side", "")).lower() != "compra":
            return None
        matches = [row for row in legacy.read_operacoes() if str(row.get("Status", "")).lower() == "aberta" and str(row.get("Estratégia", "")).lower() == "venda" and str(row.get("Ativo", "")).upper() == str(trade.get("option_code", "")).upper()]
        if len(matches) != 1:
            return None
        operation = matches[0]
        open_quantity = int(legacy.fnum(operation.get("Contratos"), 0) * legacy.load_config().get("Tamanho contrato opcoes", 100))
        note_quantity = int(trade.get("quantity", 0))
        match_type = "total" if note_quantity == open_quantity else "parcial" if 0 < note_quantity < open_quantity else "incompatível"
        return {"operation_id": str(operation.get("ID")), "option_code": str(operation.get("Ativo")), "open_quantity": open_quantity, "note_quantity": note_quantity, "match_type": match_type}

    @app.post("/api/notas-corretagem/analisar")
    def analyze_brokerage_note():
        uploaded = request.files.get("brokerage_note")
        if uploaded is None or not uploaded.filename:
            return jsonify({"ok": False, "error": "Selecione uma nota em PDF."}), 400
        if not uploaded.filename.lower().endswith(".pdf"):
            return jsonify({"ok": False, "error": "Envie um arquivo PDF."}), 400
        try:
            note = parse_btg_necton_pdf(uploaded.read())
            payload = note_to_api(note)
            for trade in payload["trades"]:
                trade["closure_candidate"] = closure_candidate(trade)
            return jsonify({"ok": True, "note": payload, "raw_pdf_stored": False})
        except BrokerageNoteError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/notas-importadas")
    def imported_brokerage_notes():
        notes = load_imported_notes(legacy)
        dashboard = build_notes_dashboard(notes)
        return render_template("notas_importadas.html", notes_dashboard=dashboard)

    @app.delete("/api/notas-importadas/<path:note_key>")
    def delete_brokerage_note(note_key: str):
        if not delete_imported_note(legacy, note_key):
            return jsonify({"ok": False, "error": "Nota importada não encontrada."}), 404
        return jsonify({"ok": True, "message": "Nota excluída e sistema recalculado."})
