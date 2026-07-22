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
        self.operations[0]["Premio_liquido"] = 150
        view = build_dashboard_view_model(self.operations, [], self.indicators, self.history, self.config)
        self.assertEqual(view.open_puts, 1)
        self.assertEqual(view.next_expiry["option_code"], "PETRT123")
        self.assertEqual(view.portfolio[0]["asset"], "PETR")
        self.assertEqual(view.ai_tone, "positive")
        self.assertEqual(view.premiums_total, 150)

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
        self.assertEqual(len(view.roll_candidates), 0)
        self.assertEqual(operational["severity"], "medium")
        self.assertEqual({category["kind"] for category in operational["categories"]}, {"Dados"})

    def test_attention_does_not_warn_when_put_is_above_strike(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("19.10"), Strike_n=Decimal("18.81"), Dias=22, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        self.assertFalse(any(item["option_code"] == "PETRT123" for item in view.attention_items))

    def test_put_above_strike_is_not_critical_only_because_expiry_is_close(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("22"), Strike_n=Decimal("18"), Dias=5, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        self.assertFalse(any(item["option_code"] == "PETRT123" for item in view.attention_items))
        self.assertEqual(view.roll_candidates, ())

    def test_put_at_or_below_strike_only_becomes_critical_with_ten_days_or_less(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("18"), Strike_n=Decimal("18"), Dias=30, Alerta="OK")
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        self.assertFalse(any(item["option_code"] == "PETRT123" for item in view.attention_items))

        near_expiry = dict(operation, Dias=10)
        view = build_dashboard_view_model([near_expiry], [], self.indicators, self.history, self.config)
        operational = next(item for item in view.attention_items if item["option_code"] == "PETRT123")
        self.assertEqual(operational["severity"], "critical")
        self.assertEqual(operational["categories"][0]["kind"], "Rolagem")
        self.assertEqual(len(view.roll_candidates), 1)

    def test_exercise_interest_changes_alert_action_and_suppresses_roll_candidate(self):
        operation = dict(self.operations[0], Cotacao_n=Decimal("17.50"), Strike_n=Decimal("18"), Dias=8, Interesse_exercicio=True)
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        alert = next(item for item in view.attention_items if item["option_code"] == "PETRT123")
        self.assertEqual(alert["severity"], "high")
        self.assertEqual(alert["categories"][0]["kind"], "Exercício")
        self.assertIn("conforme sua preferência", alert["message"])
        self.assertEqual(view.roll_candidates, ())

    def test_goau_put_above_strike_does_not_generate_attention(self):
        operation = dict(self.operations[0], Ativo="GOAUS139", Cotacao_n=Decimal("10.52"), Strike_n=Decimal("10.21"), Dias=5)
        view = build_dashboard_view_model([operation], [], self.indicators, self.history, self.config)
        self.assertFalse(any(item["option_code"] == "GOAUS139" for item in view.attention_items))
        self.assertEqual(view.roll_candidates, ())

    def test_dashboard_warns_about_asset_concentration_using_total_capital(self):
        operation = dict(self.operations[0], Capital=4000, Cotacao_n=35, Strike_n=30, Dias=40)
        indicators = dict(self.indicators, capital_comp=4000)
        view = build_dashboard_view_model([operation], [], indicators, self.history, self.config)

        self.assertEqual(view.portfolio[0]["capital_share"], 40)
        self.assertEqual(view.portfolio[0]["risk"], "high")
        self.assertFalse(any(category["kind"] == "Concentração" for item in view.attention_items for category in item["categories"]))

    def test_today_scenario_uses_nearest_expiry_and_real_option_quote(self):
        later = dict(self.operations[0], Ativo="VALEQ100", Dias=25, Premio_opcao_n=Decimal("0.80"), Cotacao_n=Decimal("70"), Strike_n=Decimal("65"))
        sooner = dict(self.operations[0], Ativo="PETRT123", Dias=4, Premio_opcao_n=Decimal("1.10"), Cotacao_n=Decimal("28"), Strike_n=Decimal("30"))
        quotes = {"PETRT123": {"price": 1.45, "source": "B3 COTAHIST EOD"}}

        view = build_dashboard_view_model([later, sooner], [], self.indicators, self.history, self.config, quotes)

        self.assertEqual(view.today_scenario[0]["option_code"], "PETRT123")
        self.assertEqual(view.today_scenario[0]["own_value"], 1.10)
        self.assertEqual(view.today_scenario[0]["current_value"], 1.45)
        self.assertEqual(view.today_scenario[0]["situation"], "Seria exercida")
        self.assertIsNone(view.today_scenario[1]["current_value"])

    def test_upcoming_expiries_include_covered_calls(self):
        covered_call = dict(
            self.operations[0],
            Ativo="CPLEH15",
            Tipo="CALL",
            Estratégia="Venda coberta",
            Capital=0,
            Dias=8,
            Vencimento_fmt="21/08/2026",
        )

        view = build_dashboard_view_model(
            [self.operations[0], covered_call], [], self.indicators, self.history, self.config
        )

        self.assertEqual(view.next_expiry["option_code"], "CPLEH15")
        self.assertEqual(
            [item["option_code"] for item in view.upcoming_expiries],
            ["CPLEH15", "PETRT123"],
        )

    def test_patrimonial_chart_uses_history_patrimony(self):
        history = [
            {"mes": "jun/26", "premios": 25, "patrimonio": 1500},
            {"mes": "jul/26", "premios": 40, "patrimonio": 1540},
        ]
        view = build_dashboard_view_model(
            self.operations, [], self.indicators, history, self.config
        )

        self.assertEqual(view.chart_labels, ("jun/26", "jul/26"))
        self.assertEqual(view.chart_premiums, (1500, 1540))

    def test_dashboard_exposes_available_cash_all_open_operations_and_next_darf(self):
        covered_call = dict(self.operations[0], Ativo="CPLEH15", Tipo="CALL", Capital=0)
        indicators = dict(self.indicators, broker_cash_balance=8000, capital_comp=3000)
        projection = {"current_month": "2026-07", "rows": [{
            "competence": "2026-07", "net_result": Decimal("100"),
            "taxable_base": Decimal("100"), "estimated_darf": Decimal("15"),
            "review_count": 0,
        }]}
        view = build_dashboard_view_model(
            [self.operations[0], covered_call], [], indicators, self.history,
            self.config, darf_projection=projection,
        )
        self.assertEqual(view.available_to_trade, 5000)
        self.assertEqual(view.open_operations, 2)
        self.assertEqual(view.darf_alert["estimated_darf"], 15)
        self.assertEqual(view.darf_alert["due_date"], "2026-08-31")


if __name__ == "__main__":
    unittest.main()
