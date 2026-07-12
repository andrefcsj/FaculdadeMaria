from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import legacy_app
from services.brokerage_note_service import (
    build_notes_dashboard,
    note_to_api,
    parse_btg_necton_pdf,
    save_imported_note,
)


BTG_TEXT = """NOTA DE CORRETAGEM
32451438
 Nr. nota
10/06/2026
 Data pregão
BTG Pactual CTVM S.A. necton
Negócios realizados
1-BOVESPA V OPCAO DE VENDA 07/26 BBDCS167 PN 100 0,33 33,00 C
Resumo dos Negócios Resumo Financeiro
33,00Valor das operações
0,00 I.R.R.F. s/ operações, base R$ 0,00
Líquido para 11/06/2026 C31,92
"""


class BrokerageNoteServiceTests(unittest.TestCase):
    def parsed(self):
        with patch("services.brokerage_note_service.extract_pdf_text", return_value=BTG_TEXT):
            return parse_btg_necton_pdf(b"fake-pdf")

    def test_parses_real_btg_necton_layout_without_inventing_fields(self):
        note = self.parsed()
        trade = note.trades[0]
        self.assertEqual(note.note_number, "32451438")
        self.assertEqual(str(note.net_cash), "31.92")
        self.assertEqual(str(note.operational_costs), "1.08")
        self.assertEqual(trade.option_code, "BBDCS167")
        self.assertEqual(trade.quantity, 100)
        self.assertEqual(str(trade.contracts), "1")
        self.assertFalse(hasattr(trade, "strike"))

    def test_saves_only_structured_data_and_prevents_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            class Legacy:
                DATA = Path(directory)
                USE_POSTGRES = False
            payload = note_to_api(self.parsed())
            payload["trade"] = payload["trades"][0]
            self.assertTrue(save_imported_note(Legacy, payload, "9"))
            self.assertFalse(save_imported_note(Legacy, payload, "9"))
            self.assertFalse(any(path.suffix == ".pdf" for path in Path(directory).iterdir()))

    def test_dashboard_cost_chart_excludes_trade_purchase_debits(self):
        notes = [{"trade_date":"2026-07-10","cash_direction":"D","net_cash":"1001.08","operational_costs":"1.08","irrf":"0"}]
        dashboard = build_notes_dashboard(notes)
        self.assertEqual(dashboard["cost_series"], [1.08])
        self.assertEqual(str(dashboard["totals"]["trade_debits"]), "1001.08")


class BrokerageNoteRoutesTests(unittest.TestCase):
    def test_notes_page_and_analyze_endpoint_exist(self):
        from app import app
        client = app.test_client()
        page = client.get("/notas-importadas")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Custos e impostos mensais", page.get_data(as_text=True))
        response = client.post("/api/notas-corretagem/analisar", data={})
        self.assertEqual(response.status_code, 400)

    def test_menu_replaces_market_import_with_notes(self):
        from app import app
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn("Notas Importadas", html)
        self.assertNotIn(">Importar Mercado</a>", html)


if __name__ == "__main__":
    unittest.main()
