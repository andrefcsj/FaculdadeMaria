import unittest

from app import app


class PremiumNavigationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_sidebar_has_distinct_radar_and_scanner_routes(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/radar-oportunidades"', page)
        self.assertIn('href="/scanner-inteligente"', page)
        self.assertIn("FaculdadeMaria", page)
        self.assertIn("Opções Inteligentes", page)

    def test_scanner_page_renders_explanation_and_filters(self):
        response = self.client.get("/scanner-inteligente")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Exploração completa do mercado", page)
        self.assertIn("Seleção priorizada", page)
        self.assertIn("scannerStatus", page)

    def test_dashboard_renders_real_kpi_insights_and_severity_panel(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertEqual(page.count('class="exec-kpi__spark"'), 0)
        self.assertEqual(page.count('class="exec-kpi__insight"'), 8)
        self.assertIn("Progresso da meta", page)
        self.assertIn("SALDO NA CORRETORA", page)
        self.assertIn("Atenção necessária", page)


if __name__ == "__main__":
    unittest.main()
