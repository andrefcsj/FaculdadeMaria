"""Painel de apuração gerencial de renda variável e memória da DARF 6015."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from flask import render_template, request

from services.closed_operations_service import build_closed_dashboard
from services.cash_ledger_service import money
from services.paid_darf_service import load_paid_darfs


def _last_weekday(year: int, month: int) -> date:
    current = date(year, month, calendar.monthrange(year, month)[1])
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current


def _due_date(competence: str) -> date:
    year, month = (int(part) for part in competence.split("-"))
    year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return _last_weekday(year, month)


def register(app, legacy):
    @app.get("/apuracao-ir")
    def income_tax_assessment():
        dashboard = build_closed_dashboard(legacy, scope="all", selected_month="")
        rows = dashboard["darf_projection"]["rows"]
        paid_by_competence = {}
        for payment in load_paid_darfs(legacy):
            competence = str(payment.get("competence", ""))
            paid_by_competence[competence] = paid_by_competence.get(competence, 0) + money(payment.get("amount"))
        for row in rows:
            row["due_date"] = _due_date(row["competence"])
            row["paid_amount"] = paid_by_competence.get(row["competence"], 0)
            row["pending_amount"] = max(row["estimated_darf"] - row["paid_amount"], 0)
            row["is_paid"] = row["estimated_darf"] > 0 and row["pending_amount"] == 0
            row["payment_status"] = "Pago" if row["is_paid"] else ("Pagamento pendente" if row["pending_amount"] > 0 else "Sem imposto")
        requested = request.args.get("competencia", "")
        selected = next((row for row in rows if row["competence"] == requested), None)
        if selected is None:
            payable = [row for row in rows if row["pending_amount"] > 0]
            selected = payable[-1] if payable else rows[-1]
        return render_template(
            "apuracao_ir.html", tax_rows=rows, selected=selected,
            revenue_code=dashboard["darf_projection"]["revenue_code"],
        )
