from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import legacy_app
from services.brokerage_note_service import note_to_api, parse_btg_necton_pdf
from services.equity_position_service import (
    delete_equity_asset, manual_equity_lot, portfolio, replace_equity_asset,
    replace_equity_lot_from_note, save_equity_lot, sell_equity_asset,
    validate_covered_call,
)
from services.new_operation_extension import _preview_roi


EXERCISE_TEXT = """BTG Pactual CTVM S.A. Necton
17/07/2026
Folha  Data pregão
NOTA DE CORRETAGEM PRÉVIA
1-BOVESPA C EOV CPLES15E 100 15,28 1.528,00 D
Resumo dos Negócios
1.528,00Valor das operações
I.R.R.F. s/ operações, base R$ 0,00
Líquido: D1.529,50
"""

EQUITY_PURCHASE_TEXT = """NOTA DE CORRETAGEM
33445566
17/07/2026 Data pregão
BTG Pactual CTVM S.A. Necton
Negócios realizados
1-BOVESPA C VISTA CPLE3 ON NM 100 14,70 1.470,00 D
Resumo dos Negócios
1.470,00Valor das operações
0,00 I.R.R.F. s/ operações, base R$ 0,00
Líquido para 20/07/2026 D1.471,50
"""


def test_preliminary_put_assignment_is_parsed_without_inventing_note_number():
    with patch("services.brokerage_note_service.extract_pdf_text", return_value=EXERCISE_TEXT):
        payload = note_to_api(parse_btg_necton_pdf(b"exercise-note"))
    trade = payload["trades"][0]
    assert payload["note_number"].startswith("EXERCICIO-20260717-")
    assert payload["cash_direction"] == "D"
    assert payload["net_cash"] == "1529.50"
    assert payload["operational_costs"] == "1.50"
    assert trade["option_code"] == "CPLES15"
    assert trade["event_type"] == "exercise_put_assignment"


def test_cash_equity_purchase_is_recognized_for_portfolio():
    with patch("services.brokerage_note_service.extract_pdf_text", return_value=EQUITY_PURCHASE_TEXT):
        payload = note_to_api(parse_btg_necton_pdf(b"equity-note"))
    trade = payload["trades"][0]
    assert trade["event_type"] == "equity_purchase"
    assert trade["underlying_asset"] == "CPLE3"
    assert trade["quantity"] == 100
    assert trade["unit_price"] == "14.70"
    assert trade["allocated_costs"] == "1.50"


def test_preliminary_regular_note_without_number_is_accepted_and_marked():
    preliminary = EQUITY_PURCHASE_TEXT.replace("33445566\n", "")
    with patch("services.brokerage_note_service.extract_pdf_text", return_value=preliminary):
        payload = note_to_api(parse_btg_necton_pdf(b"preliminary-regular-note"))
    assert payload["is_provisional"] is True
    assert payload["note_number"].startswith("PREVIA-20260717-")
    assert payload["trades"][0]["option_code"] == "CPLE3"


def test_covered_call_uses_shares_and_never_adds_strike_capital():
    row = {"ID":"1", "Data abertura":"2026-07-17", "Ativo":"CPLEH160", "Tipo":"CALL", "Estratégia":"Venda Coberta", "Status":"Aberta", "Contratos":"1", "Strike":"16", "Premio_opcao":"0.30", "Custos":"1", "IRRF":"0", "Vencimento":"2026-08-21", "Cotacao_atual":"14.80", "Resultado_realizado":"0"}
    enriched = legacy_app.enrich_ops([row], legacy_app.load_config())[0]
    assert enriched["Capital"] == 0
    assert enriched["Fluxo_liquido"] == 29


def test_coverage_validation_blocks_more_calls_than_free_shares():
    with TemporaryDirectory() as directory:
        class Legacy:
            DATA = Path(directory)
            USE_POSTGRES = False
            read_operacoes = staticmethod(lambda: [])
            load_config = staticmethod(lambda: {"Tamanho contrato opcoes": 100})
            infer_acao_from_option = staticmethod(lambda _code: "CPLE3")
        save_equity_lot(Legacy, {"lot_id":"exercise:27", "asset":"CPLE3", "quantity":100, "available_quantity":100, "cash_cost_total":"1529.50", "tax_cost_total":"1484.50"})
        assert portfolio(Legacy)[0]["available_quantity"] == 100
        assert validate_covered_call(Legacy, "CPLE3", Decimal("1")) == 0
        try:
            validate_covered_call(Legacy, "CPLE3", Decimal("2"))
            assert False, "deveria rejeitar cobertura insuficiente"
        except ValueError as exc:
            assert "Cobertura insuficiente" in str(exc)


def test_manual_portfolio_actions_recalculate_quantity_and_cost():
    with TemporaryDirectory() as directory:
        class Legacy:
            DATA = Path(directory)
            USE_POSTGRES = False
            read_operacoes = staticmethod(lambda: [])
            load_config = staticmethod(lambda: {"Tamanho contrato opcoes": 100})
            infer_acao_from_option = staticmethod(lambda code: code[:4])
        lot = manual_equity_lot(asset="LFTB11", quantity=200, average_price=Decimal("10"), acquisition_date="2026-07-22")
        assert save_equity_lot(Legacy, lot)
        assert portfolio(Legacy)[0]["tax_cost_total"] == 2000
        replace_equity_asset(Legacy, asset="LFTB11", quantity=150, average_price=Decimal("11"), acquisition_date="2026-07-22")
        assert portfolio(Legacy)[0]["tax_cost_total"] == 1650
        consumed = sell_equity_asset(Legacy, asset="LFTB11", quantity=50)
        assert consumed == 550
        assert portfolio(Legacy)[0]["quantity"] == 100
        assert delete_equity_asset(Legacy, "LFTB11") is True
        assert portfolio(Legacy) == []


def test_definitive_note_replaces_equity_lot_without_duplicating_quantity():
    with TemporaryDirectory() as directory:
        class Legacy:
            DATA = Path(directory)
            USE_POSTGRES = False
            read_operacoes = staticmethod(lambda: [])
            load_config = staticmethod(lambda: {"Tamanho contrato opcoes": 100})
            infer_acao_from_option = staticmethod(lambda code: code[:4])

        preview = {
            "lot_id": "purchase:preview:0", "asset": "PETR4",
            "quantity": 100, "available_quantity": 100,
            "cash_cost_total": "3000", "tax_cost_total": "3000",
            "source_note_key": "preview:0", "note_pending": True,
        }
        definitive = {
            "lot_id": "purchase:final:0", "asset": "PETR4",
            "quantity": 100, "available_quantity": 100,
            "cash_cost_total": "3010", "tax_cost_total": "3010",
            "source_note_key": "final:0", "note_pending": False,
        }
        assert save_equity_lot(Legacy, preview)
        assert replace_equity_lot_from_note(Legacy, "preview:0", definitive)
        holdings = portfolio(Legacy)
        assert len(holdings) == 1
        assert holdings[0]["quantity"] == 100
        assert holdings[0]["available_quantity"] == 100
        assert holdings[0]["tax_cost_total"] == 3010
        assert holdings[0]["note_pending"] is False


def test_new_operation_keeps_original_sale_purchase_controls():
    template = (Path(__file__).parents[1] / "templates" / "components" / "new_operation_modal.html").read_text(encoding="utf-8")
    assert 'value="Venda" checked><label for="newVenda">Venda</label>' in template
    assert 'value="Compra"><label for="newCompra">Compra</label>' in template
    assert 'id="newCoveredCall"' not in template


def test_preview_roi_uses_net_premium_and_nominal_strike_capital():
    roi = _preview_roi(
        strategy="Venda", contracts=Decimal("1"), strike=Decimal("10"),
        premium=Decimal("0.25"), costs=Decimal("2"), irrf=Decimal("0"),
    )
    assert roi == Decimal("2.3")


def test_new_operation_popup_has_live_roi_probability_and_colored_types():
    root = Path(__file__).parents[1]
    template = (root / "templates" / "components" / "new_operation_modal.html").read_text(encoding="utf-8")
    script = (root / "static" / "new_operation.js").read_text(encoding="utf-8")
    styles = (root / "static" / "new_operation_preview.css").read_text(encoding="utf-8")
    assert 'id="newPreviewRoi"' in template
    assert 'id="newPreviewExercise"' in template
    assert "/api/operacoes/preview" in script
    assert "roi >= 2 ? 'is-good' : roi >= 1 ? 'is-medium' : 'is-low'" in script
    assert 'label[for="newCall"]' in styles
    assert 'label[for="newPut"]' in styles
