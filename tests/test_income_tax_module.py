from datetime import date

from app import app
from services.income_tax_extension import _attach_payment_operations, _due_date
from services.darf_pdf_service import generate_darf_pdf
from pypdf import PdfReader


def test_darf_due_date_uses_last_weekday_of_following_month():
    assert _due_date("2026-07") == date(2026, 8, 31)
    assert _due_date("2026-12") == date(2027, 1, 29)


def test_income_tax_page_and_management_menu_are_available():
    client = app.test_client()

    response = client.get("/apuracao-ir")
    assert response.status_code == 200
    assert b"DARF 6015" in response.data
    assert b"Mem" in response.data
    assert "Operações comuns" in response.get_data(as_text=True)
    assert b"Day trade" in response.data
    assert "modelo visual do Sicalc" in response.get_data(as_text=True)
    assert "taxOperationsDialog" in response.get_data(as_text=True)
    assert "DARFs por competência" in response.get_data(as_text=True)
    assert "https://sicalc.receita.fazenda.gov.br/sicalc/rapido/calculo" in response.get_data(as_text=True)

    menu = client.get("/").get_data(as_text=True)
    assert "Apuração de IR" in menu
    assert menu.index("Apuração de IR") < menu.index("DARFs Pagos")
    assert menu.count("Radar Jade Lizard") == 1


def test_resolved_broker_observation_is_not_rendered():
    html = app.test_client().get("/notas-importadas").get_data(as_text=True)
    assert "CONFERIR COM A CORRETORA" not in html


def test_simple_darf_pdf_contains_payment_fields():
    pdf = generate_darf_pdf(
        profile={"name":"Maria Teste","cpf":"12345678901","phone":"","city":"São Paulo","state":"SP"},
        competence="2026-08", due_date=date(2026, 9, 30), amount="56.01",
    )
    text = PdfReader(pdf).pages[0].extract_text()
    assert "6015" in text
    assert "56,01" in text
    assert "1a. via" in text
    assert "2a. via" in text
    assert text.count("NÚMERO DO CPF OU CNPJ") == 2


def test_missing_taxpayer_data_redirects_instead_of_raising_server_error():
    response = app.test_client().get("/apuracao-ir/darf.pdf?competencia=2026-07")
    assert response.status_code in (302, 200)


def test_total_darf_includes_operations_carried_from_previous_months():
    rows = [
        {"competence":"2026-06", "tax_operations":[{"option_code":"AAA"}], "estimated_darf":0, "tax_carry":3},
        {"competence":"2026-07", "tax_operations":[{"option_code":"BBB"}], "estimated_darf":14, "tax_carry":0},
    ]
    _attach_payment_operations(rows)
    assert [item["option_code"] for item in rows[0]["payment_operations"]] == ["AAA"]
    assert [item["option_code"] for item in rows[1]["payment_operations"]] == ["AAA", "BBB"]
