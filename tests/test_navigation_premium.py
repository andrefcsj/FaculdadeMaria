import unittest
from unittest.mock import patch

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
        self.assertIn("Simulador de Exercício", page)
        self.assertIn('href="/carteira"', page)
        self.assertIn("Carteira de Ações", page)
        self.assertIn('href="/carteira-acoes"', page)
        self.assertIn("Radar de CALL Coberta", page)
        self.assertIn('/radar-oportunidades?scan=calls#calls-cobertas', page)

    def test_exercise_simulator_is_not_redirected_to_equity_portfolio(self):
        response = self.client.get("/carteira")
        self.assertEqual(response.status_code, 200)
        self.assertIn("RESUMO DA CARTEIRA", response.get_data(as_text=True).upper())

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
        self.assertIn("Prêmios e caixa líquido das opções", page)
        self.assertIn("Crédito bruto nas vendas", page)
        self.assertIn("Valor líquido no caixa", page)
        self.assertIn("Totais do período", page)

    def test_premium_filters_route_and_validation(self):
        from tests.test_premium_history_service import PremiumHistoryServiceTests
        fixture = PremiumHistoryServiceTests()
        fixture.setUp()
        with patch("app.legacy.load_all", return_value=(fixture.operations, [], {})):
            response = self.client.get("/premios-recebidos?asset=PETR4&period=range&start_date=2026-08-12&end_date=2026-08-12")
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            self.assertIn('name="asset"', page)
            self.assertIn('value="PETR4" selected', page)
            self.assertIn("PETRT500", page)
            self.assertNotIn("BBDCT20", page)
            self.assertIn("R$ 303,50", page)
            invalid = self.client.get("/premios-recebidos?start_date=2026-09-01&end_date=2026-08-01").get_data(as_text=True)
            self.assertIn('role="alert"', invalid)
            self.assertIn("A data final deve ser igual ou posterior", invalid)
            empty = self.client.get("/premios-recebidos?asset=PETR4&month=2025-01").get_data(as_text=True)
            self.assertIn("Nenhum prêmio encontrado", empty)
            self.assertNotIn("PETRT500", empty)


if __name__ == "__main__":
    unittest.main()
