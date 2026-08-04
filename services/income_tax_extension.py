"""Painel de apuração gerencial de renda variável e memória da DARF 6015."""
from __future__ import annotations

import calendar
from datetime import date, timedelta

from flask import redirect, render_template, request, send_file, url_for

from services.closed_operations_service import build_closed_dashboard
from services.cash_ledger_service import money
from services.paid_darf_service import load_paid_darfs
from services.taxpayer_profile_service import load_taxpayer_profile, save_taxpayer_profile
from services.darf_pdf_service import generate_darf_pdf


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
    def assessment_rows():
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
            row["insufficient"] = row["estimated_darf"] == 0 and row["tax_carry"] > 0
            row["is_paid"] = row["estimated_darf"] > 0 and row["pending_amount"] == 0
            row["payment_status"] = "Pago" if row["is_paid"] else ("Pagamento pendente" if row["pending_amount"] > 0 else ("Valor insuficiente para gerar DARF" if row["insufficient"] else "Sem imposto"))
        return dashboard, rows

    @app.get("/apuracao-ir")
    def income_tax_assessment():
        dashboard, rows = assessment_rows()
        requested = request.args.get("competencia", "")
        selected = next((row for row in rows if row["competence"] == requested), None)
        if selected is None:
            payable = [row for row in rows if row["pending_amount"] > 0]
            selected = payable[-1] if payable else rows[-1]
        years = sorted({row["competence"][:4] for row in rows}, reverse=True)
        selected_year = request.args.get("ano", selected["competence"][:4])
        return render_template(
            "apuracao_ir.html", tax_rows=rows, selected=selected, taxpayer=load_taxpayer_profile(legacy),
            history_rows=[row for row in rows if row["competence"].startswith(selected_year)], years=years, selected_year=selected_year, today=date.today(),
            tax_message=request.args.get("mensagem", ""), tax_error=request.args.get("erro", ""),
            revenue_code=dashboard["darf_projection"]["revenue_code"],
        )

    @app.post("/apuracao-ir/contribuinte")
    def save_income_tax_taxpayer():
        competence = request.form.get("competence", "")
        try:
            save_taxpayer_profile(legacy, request.form)
            return redirect(url_for("income_tax_assessment", competencia=competence, mensagem="Dados do contribuinte salvos."))
        except ValueError as exc:
            return redirect(url_for("income_tax_assessment", competencia=competence, erro=str(exc)))

    @app.get("/apuracao-ir/darf.pdf")
    def download_income_tax_darf():
        competence = request.args.get("competencia", "")
        _dashboard, rows = assessment_rows(); row = next((item for item in rows if item["competence"] == competence), None)
        if not row or row["pending_amount"] < 10:
            return redirect(url_for("income_tax_assessment", competencia=competence, erro="Valor insuficiente para gerar DARF. Ele continuará acumulado para os próximos meses."))
        if row["due_date"] < date.today():
            return redirect(url_for("income_tax_assessment", competencia=competence, erro="Esta DARF está vencida. Emita a guia atualizada no Sicalc para incluir multa e juros corretamente."))
        profile = load_taxpayer_profile(legacy)
        if not all(profile.get(field) for field in ("name", "cpf", "city", "state")):
            return redirect(url_for("income_tax_assessment", competencia=competence, erro="Preencha os dados do contribuinte antes de gerar a guia."))
        pdf = generate_darf_pdf(profile=profile, competence=competence, due_date=row["due_date"], amount=row["pending_amount"])
        return send_file(pdf, mimetype="application/pdf", as_attachment=True, download_name=f"DARF-6015-{competence}.pdf")
