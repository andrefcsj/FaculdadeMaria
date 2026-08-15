import unittest

from app import app


class PremiumNavigationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_sidebar_keeps_radar_without_scanner(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn('href="/radar-oportunidades"', page)
        self.assertNotIn('href="/scanner-inteligente"', page)
        self.assertIn("FaculdadeMaria", page)
        self.assertIn("Opções Inteligentes", page)
        self.assertLess(page.index("GESTÃO"), page.index("INTELIGÊNCIA"))

    def test_scanner_route_is_removed(self):
        response = self.client.get("/scanner-inteligente")
        self.assertEqual(response.status_code, 404)

    def test_dashboard_renders_real_kpi_insights_and_severity_panel(self):
        page = self.client.get("/").get_data(as_text=True)
        self.assertEqual(page.count('class="exec-kpi__spark"'), 0)
        self.assertEqual(page.count('class="exec-kpi__insight"'), 6)
        self.assertIn("Progresso da meta", page)
        self.assertIn("PATRIMÔNIO", page)
        self.assertIn("SALDO PARA OPERAR", page)
        self.assertIn("CAPITAL COMPROMETIDO", page)
        self.assertIn("PRÊMIOS DO MÊS", page)
        self.assertNotIn("SALDO NA CORRETORA", page)
        self.assertNotIn("PRÓXIMO VENCIMENTO</small>", page)
        self.assertIn("Atenção necessária", page)
        self.assertIn('href="/premios-recebidos"', page)
        self.assertIn('href="/premios-recebidos?month=', page)

    def test_premium_history_page_is_available(self):
        page = self.client.get("/premios-recebidos").get_data(as_text=True)
        self.assertIn("Todos os prêmios recebidos", page)
        self.assertIn("Prêmio integral", page)
        self.assertIn("Prêmio líquido", page)
        self.assertIn("Totais do período", page)


if __name__ == "__main__":
    unittest.main()
