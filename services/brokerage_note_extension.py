"""Rotas de importação e painel de notas BTG/Necton."""
from __future__ import annotations

from flask import jsonify, render_template, request

from services.brokerage_note_service import (
    BrokerageNoteError,
    build_notes_dashboard,
    load_imported_notes,
    note_to_api,
    parse_btg_necton_pdf,
)


def register(app, legacy):
    @app.post("/api/notas-corretagem/analisar")
    def analyze_brokerage_note():
        uploaded = request.files.get("brokerage_note")
        if uploaded is None or not uploaded.filename:
            return jsonify({"ok": False, "error": "Selecione uma nota em PDF."}), 400
        if not uploaded.filename.lower().endswith(".pdf"):
            return jsonify({"ok": False, "error": "Envie um arquivo PDF."}), 400
        try:
            note = parse_btg_necton_pdf(uploaded.read())
            return jsonify({"ok": True, "note": note_to_api(note), "raw_pdf_stored": False})
        except BrokerageNoteError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/notas-importadas")
    def imported_brokerage_notes():
        notes = load_imported_notes(legacy)
        dashboard = build_notes_dashboard(notes)
        return render_template("notas_importadas.html", notes_dashboard=dashboard)
