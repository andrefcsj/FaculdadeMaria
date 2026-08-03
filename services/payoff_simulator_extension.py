"""Página do simulador educacional de payoff."""
from __future__ import annotations

from flask import render_template


def register(app, _legacy):
    @app.get("/estrategias/simulador-payoff")
    def simulador_payoff():
        return render_template("simulador_payoff.html")
