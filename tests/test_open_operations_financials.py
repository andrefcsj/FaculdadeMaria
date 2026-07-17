from datetime import date
from unittest.mock import patch

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
