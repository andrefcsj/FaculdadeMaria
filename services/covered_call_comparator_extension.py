"""Página independente para comparação de CALLs cobertas."""
from __future__ import annotations

from flask import render_template


def register(app, _legacy):
    @app.get("/estrategias/comparador-call-coberta")
    def comparador_call_coberta():
        return render_template("comparador_call_coberta.html")
