import unittest

from app import app


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


if __name__ == "__main__":
    unittest.main()
