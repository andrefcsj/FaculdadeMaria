import json
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import legacy_app
from services.brokerage_note_service import (
    build_notes_dashboard,
    delete_imported_note,
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

MIXED_BTG_TEXT = """NOTA DE CORRETAGEM
32813199
 Nr. nota
29/06/2026
 Data pregão
BTG Pactual CTVM S.A. necton
Negócios realizados
1-BOVESPA C OPCAO DE VENDA 07/26 BBDCS167 PN 100 0,06 6,00 D
1-BOVESPA V OPCAO DE VENDA 07/26 BBDCS183 PN 100 0,44 44,00 C
Resumo dos Negócios Resumo Financeiro
50,00Valor das operações
0,00 I.R.R.F. s/ operações, base R$ 0,00
Líquido para 30/06/2026 C35,84
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
            self.assertTrue(delete_imported_note(Legacy, f"{payload['document_hash']}:0"))
            self.assertFalse(delete_imported_note(Legacy, "inexistente"))

    def test_dashboard_cost_chart_excludes_trade_purchase_debits(self):
        notes = [{"trade_date":"2026-07-10","cash_direction":"D","net_cash":"1001.08","operational_costs":"1.08","irrf":"0"}]
        dashboard = build_notes_dashboard(notes)
        self.assertEqual(dashboard["cost_series"], [1.08])
        self.assertEqual(str(dashboard["totals"]["trade_debits"]), "1001.08")

    def test_mixed_note_uses_signed_trades_and_persists_each_trade_once(self):
        with patch("services.brokerage_note_service.extract_pdf_text", return_value=MIXED_BTG_TEXT):
            note = parse_btg_necton_pdf(b"mixed-note")
        self.assertEqual(str(note.net_cash), "35.84")
        self.assertEqual(str(note.operational_costs), "2.16")
        self.assertEqual([str(trade.allocated_costs) for trade in note.trades], ["0.26", "1.90"])

        with tempfile.TemporaryDirectory() as directory:
            class Legacy:
                DATA = Path(directory)
                USE_POSTGRES = False

            payload = note_to_api(note)
            first = {**payload, "trade": payload["trades"][0]}
            second = {**payload, "trade": payload["trades"][1]}
            self.assertTrue(save_imported_note(Legacy, first, "10"))
            self.assertTrue(save_imported_note(Legacy, second, "11"))
            saved = json.loads((Path(directory) / "brokerage_notes.json").read_text(encoding="utf-8"))
            self.assertEqual([row["cash_direction"] for row in saved], ["D", "C"])
            self.assertEqual([row["net_cash"] for row in saved], ["6.26", "42.10"])
            signed_total = -Decimal(saved[0]["net_cash"]) + Decimal(saved[1]["net_cash"])
            self.assertEqual(signed_total, Decimal("35.84"))


class BrokerageNoteRoutesTests(unittest.TestCase):
    def test_notes_page_and_analyze_endpoint_exist(self):
        from app import app
        client = app.test_client()
        page = client.get("/notas-importadas")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Custos e impostos mensais", page.get_data(as_text=True))
        response = client.post("/api/notas-corretagem/analisar", data={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("newSummaryValueLabel", page.get_data(as_text=True))

    def test_menu_replaces_market_import_with_notes(self):
        from app import app
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn("Importar Notas", html)
        self.assertNotIn(">Notas Importadas</a>", html)
        self.assertNotIn(">Importar Mercado</a>", html)

    def test_debit_note_has_red_label_in_imported_notes_list(self):
        from app import app
        with tempfile.TemporaryDirectory() as directory, patch.object(legacy_app, "DATA", Path(directory)):
            record = [{
                "key":"debit:0", "document_hash":"debit", "note_number":"10", "broker":"BTG Pactual / Necton",
                "trade_date":"2026-06-29", "cash_direction":"D", "gross_operations":"6.00", "net_cash":"6.26",
                "operational_costs":"0.26", "irrf":"0", "operation_id":"1",
                "trade":{"option_code":"BBDCS167", "side":"Compra", "quantity":100},
            }]
            (Path(directory) / "brokerage_notes.json").write_text(json.dumps(record), encoding="utf-8")
            html = app.test_client().get("/notas-importadas").get_data(as_text=True)
        self.assertIn('class="notes-tag debit">Débito</span>', html)

    def test_note_import_scopes_side_and_type_to_new_operation_form(self):
        script = (Path(__file__).parents[1] / "static" / "brokerage_note_import.js").read_text(encoding="utf-8")
        self.assertIn("const operationForm = document.getElementById('newOperationForm')", script)
        self.assertIn("operationForm.querySelector(`input[name=\"Estrategia\"]", script)
        self.assertIn("operationForm.querySelector(`input[name=\"Tipo\"]", script)


if __name__ == "__main__":
    unittest.main()
