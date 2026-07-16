import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import app
import legacy_app


class RadarGuidedFlowTests(unittest.TestCase):
    def test_radar_explains_update_sequence(self):
        html = app.test_client().get("/radar-oportunidades").get_data(as_text=True)
        expected = [
            "1. Atualizar dados B3",
            "2. Atualizar qualidade CVM",
            "3. Ir para as oportunidades",
            "4. Avaliar resultado",
        ]
        positions = [html.index(label) for label in expected]
        self.assertEqual(positions, sorted(positions))

    def test_radar_keeps_csv_as_manual_alternative(self):
        html = app.test_client().get("/radar-oportunidades").get_data(as_text=True)
        self.assertIn("Ou envie seu arquivo manualmente:", html)
        self.assertIn('action="/radar-oportunidades/importar-mercado"', html)
        self.assertNotIn("<details", html)

    def test_radar_explains_data_reliability(self):
        html = app.test_client().get("/radar-oportunidades").get_data(as_text=True)
        self.assertIn("Confiabilidade dos dados", html)
        self.assertIn("Confiança informada", html)
        self.assertIn("independente da nota da oportunidade", html)

    def test_step_three_uses_profitpro_and_requires_confirmed_strike(self):
        template = (Path(__file__).parents[1] / "templates" / "radar_oportunidades.html").read_text(encoding="utf-8")
        self.assertIn("PASSO 3 • Confirmar preço no ProfitPro", template)
        self.assertIn('required name="strike"', template)
        self.assertNotIn("Confirmar preço atual no BTG", template)

    def test_manual_radar_confirmation_persists_strike_for_recalculation(self):
        with tempfile.TemporaryDirectory() as directory:
            quotes = Path(directory) / "manual_quotes.json"
            with patch.object(legacy_app, "RADAR_QUOTES", quotes):
                response = app.test_client().post("/radar-oportunidades/preco-intraday", data={
                    "option_code": "PETRQ300", "strike": "29,75", "premium": "1,55",
                    "bid": "1,50", "ask": "1,60",
                })
            self.assertEqual(response.status_code, 302)
            saved = json.loads(quotes.read_text(encoding="utf-8"))["PETRQ300"]
            self.assertEqual(saved["strike"], 29.75)
            self.assertEqual(saved["premium"], 1.55)


if __name__ == "__main__":
    unittest.main()
