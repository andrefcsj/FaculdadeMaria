from datetime import date
from unittest.mock import patch
from pathlib import Path

import legacy_app


def test_purchase_does_not_reserve_strike_capital_and_total_roi_uses_signed_flow():
    rows = [
        {"ID": "1", "Ativo": "CPLES15", "Tipo": "PUT", "Estratégia": "Venda", "Status": "Aberta", "Contratos": "1", "Strike": "15.28", "Premio_opcao": "0.45", "Custos": "1.10", "IRRF": "0", "Vencimento": "2026-07-17", "Cotacao_atual": "14.80"},
        {"ID": "2", "Ativo": "CPLES129", "Tipo": "PUT", "Estratégia": "Compra", "Status": "Aberta", "Contratos": "1", "Strike": "12.78", "Premio_opcao": "0.02", "Custos": "1.05", "IRRF": "0", "Vencimento": "2026-07-17", "Cotacao_atual": "14.80"},
    ]
    with patch("legacy_app.date") as mocked_date:
        mocked_date.today.return_value = date(2026, 7, 17)
        enriched = legacy_app.enrich_ops(rows, {"Tamanho contrato opcoes": 100})
    assert enriched[0]["Capital"] == 1528
    assert enriched[0]["Fluxo_liquido"] == 43.9
    assert enriched[1]["Capital"] == 0
    assert enriched[1]["Fluxo_liquido"] == -3.05
    total_result = sum(row["Fluxo_liquido"] for row in enriched)
    total_capital = sum(row["Capital"] for row in enriched)
    assert round(total_result / total_capital * 100, 2) == 2.67


def test_open_operations_labels_purchase_as_debit():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert "Crédito / débito" in template
    assert "Débito líquido" in template
    assert "-o.Fluxo_liquido" in template


def test_dashboard_month_window_keeps_history_and_only_one_future_month():
    with patch("legacy_app.date") as mocked_date:
        mocked_date.today.return_value = date(2026, 7, 22)
        mocked_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
        labels = legacy_app.rolling_months()

    assert labels[0] == "ago/25"
    assert labels[-3:] == ["jun/26", "jul/26", "ago/26"]
    assert len(labels) == 13


def test_covered_call_does_not_add_cash_to_committed_capital():
    rows = [
        {"ID": "1", "Ativo": "BBDCT20", "Tipo": "PUT", "Estratégia": "Venda", "Status": "Aberta", "Contratos": "1", "Strike": "18.81", "Premio_opcao": "0.64", "Custos": "1.95", "IRRF": "0", "Vencimento": "2026-08-21"},
        {"ID": "2", "Ativo": "CPLET150", "Tipo": "PUT", "Estratégia": "Venda", "Status": "Aberta", "Contratos": "1", "Strike": "14.80", "Premio_opcao": "0.40", "Custos": "1.20", "IRRF": "0", "Vencimento": "2026-08-21"},
        {"ID": "3", "Ativo": "CPLEH15", "Tipo": "CALL", "Estratégia": "Venda coberta", "Status": "Aberta", "Contratos": "1", "Strike": "15.00", "Premio_opcao": "0.32", "Custos": "1.00", "IRRF": "0", "Vencimento": "2026-08-21"},
    ]
    enriched = legacy_app.enrich_ops(rows, {"Tamanho contrato opcoes": 100})

    assert [round(operation["Capital"], 2) for operation in enriched] == [1881, 1480, 0]
    assert round(sum(operation["Capital"] for operation in enriched), 2) == 3361
