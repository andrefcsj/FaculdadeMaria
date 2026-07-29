import unittest

from services.premium_history_service import build_premium_history


class LegacyStub:
    @staticmethod
    def load_config():
        return {"Tamanho contrato opcoes": 100}

    @staticmethod
    def parse_date(value):
        from datetime import date
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def infer_acao_from_option(code):
        return {"BBDC": "BBDC4", "PETR": "PETR4"}.get(code[:4], code[:4])


class PremiumHistoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.operations = [
            {"Data abertura": "2026-07-10", "Ativo": "BBDCT20", "Estratégia": "Venda", "Contratos": 1, "Premio_opcao": 0.64, "Premio_bruto": 64, "Premio_liquido": 62.05},
            {"Data abertura": "2026-08-12", "Ativo": "PETRT500", "Estratégia": "Venda", "Contratos": 2, "Premio_opcao": 1.53, "Premio_bruto": 306, "Premio_liquido": 303.50},
            {"Data abertura": "2026-08-13", "Ativo": "PETRT500", "Estratégia": "Compra", "Contratos": 1, "Premio_opcao": 1.2, "Premio_bruto": 120, "Premio_liquido": 118},
        ]

    def test_builds_automatic_gross_and_net_premium_history(self):
        result = build_premium_history(LegacyStub, self.operations)

        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(result["total_quantity"], 300)
        self.assertEqual(result["total_gross"], 370)
        self.assertEqual(result["total_net"], 365.55)
        self.assertEqual(result["rows"][0]["asset"], "PETR4")

    def test_filters_by_month_or_year(self):
        month = build_premium_history(LegacyStub, self.operations, selected_month="2026-07")
        year = build_premium_history(LegacyStub, self.operations, selected_year="2026")

        self.assertEqual([row["option_code"] for row in month["rows"]], ["BBDCT20"])
        self.assertEqual(len(year["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
