import unittest
from decimal import Decimal

from services.dashboard_service import build_dashboard_view_model


class DashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.operations = [{
            "Ativo": "PETRT123", "Tipo": "PUT", "Status": "Aberta",
            "Capital": 3000, "ROI": 4.5, "Dias": 12,
            "Vencimento_fmt": "23/07/2026", "Alerta": "OK",
            "Cotacao_n": 31,
        }]
        self.indicators = {
            "lucro_mes": 150, "roi_medio_abertas": 4.5,
            "capital_comp": 3000, "roi_abertas": 4.5,
            "capital_total": 10000, "caixa_livre": 7000,
        }
        self.history = [{"mes": "Jul/26", "premios": 150}]
        self.config = {"Meta ROI mensal": 0.04}

    def test_builds_real_dashboard_summary(self):
        view = build_dashboard_view_model(self.operations, [], self.indicators, self.history, self.config)
        self.assertEqual(view.open_puts, 1)
        self.assertEqual(view.next_expiry["option_code"], "PETRT123")
        self.assertEqual(view.portfolio[0]["asset"], "PETR")
        self.assertEqual(view.ai_tone, "positive")

    def test_does_not_invent_opportunities_for_empty_portfolio(self):
        indicators = dict(self.indicators, roi_medio_abertas=0, capital_comp=0, roi_abertas=0)
        view = build_dashboard_view_model([], [], indicators, [], self.config)
        self.assertEqual(view.open_puts, 0)
        self.assertIsNone(view.next_expiry)
        self.assertEqual(view.roll_candidates, ())
        self.assertIn("Não há PUTs abertas", view.ai_summary)

    def test_attention_uses_existing_operational_data(self):
        operation = dict(self.operations[0], Cotacao_n=0, Dias=4, Alerta="PUT dentro do dinheiro")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        operational = next(item for item in view.attention_items if item["option_code"] == "PETRT123")
        self.assertIn("cotação não informada", operational["message"].lower())
        self.assertEqual(len(view.roll_candidates), 1)
        self.assertEqual(operational["severity"], "high")
        self.assertEqual({category["kind"] for category in operational["categories"]}, {"Vencimento", "Dados"})

    def test_attention_warns_when_put_is_close_to_strike(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("19.10"), Strike_n=Decimal("18.81"), Dias=22, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        operational = next(item for item in view.attention_items if item["option_code"] == "PETRT123")
        self.assertEqual(operational["severity"], "high")
        self.assertIn("risco elevado", operational["message"])

    def test_put_above_strike_is_not_critical_only_because_expiry_is_close(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("22"), Strike_n=Decimal("18"), Dias=5, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        operational = next(item for item in view.attention_items if item["option_code"] == "PETRT123")

        self.assertEqual(operational["severity"], "high")
        self.assertEqual([category["kind"] for category in operational["categories"]], ["Vencimento"])
        self.assertNotIn("dentro do dinheiro", operational["message"])

    def test_put_at_or_below_strike_remains_critical_for_exercise_risk(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("18"), Strike_n=Decimal("18"), Dias=30, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        operational = next(item for item in view.attention_items if item["option_code"] == "PETRT123")

        self.assertEqual(operational["severity"], "critical")
        self.assertEqual(operational["categories"][0]["kind"], "Exercício")

    def test_dashboard_warns_about_asset_concentration_using_total_capital(self):
        operation = dict(self.operations[0], Capital=4000, Cotacao_n=35, Strike_n=30, Dias=40)
        indicators = dict(self.indicators, capital_comp=4000)
        view = build_dashboard_view_model([operation], [], indicators, self.history, self.config)

        self.assertEqual(view.portfolio[0]["capital_share"], 40)
        self.assertEqual(view.portfolio[0]["risk"], "high")
        self.assertTrue(any(category["kind"] == "Concentração" for item in view.attention_items for category in item["categories"]))


if __name__ == "__main__":
    unittest.main()
