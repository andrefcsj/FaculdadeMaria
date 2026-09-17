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

    def test_asset_and_inclusive_date_range_recalculate_totals(self):
        operations = self.operations + [
            {"Data abertura": "2026-08-31", "Ativo": "PETRU500", "Contratos": 1, "Premio_bruto": 100, "Premio_liquido": 95},
            {"Data abertura": "2026-09-01", "Ativo": "PETRU500", "Contratos": 1, "Premio_bruto": 200},
            {"Data abertura": "2026-08-20", "Ativo": "BBDCU20", "Contratos": 1, "Premio_bruto": 50},
        ]
        result = build_premium_history(LegacyStub, operations, selected_asset=" petr4 ", start_date="2026-08-12", end_date="2026-08-31")
        self.assertEqual([row["date"] for row in result["rows"]], ["2026-08-31", "2026-08-12"])
        self.assertEqual(result["total_gross"], 406)
        self.assertEqual(result["total_net"], 398.5)
        self.assertEqual(result["total_quantity"], 300)
        self.assertEqual(result["assets"], ("BBDC4", "PETR4"))

    def test_asset_month_and_empty_results(self):
        for asset, month, count in [("PETR4", "2026-08", 1), ("PETR4", "2026-07", 0), ("PETR4", "2025-01", 0), ("UNKNOWN", "2026-08", 0)]:
            with self.subTest(asset=asset, month=month):
                result = build_premium_history(LegacyStub, self.operations, selected_asset=asset, selected_month=month)
                self.assertEqual(len(result["rows"]), count)
                self.assertFalse(result["errors"])
                if not count:
                    self.assertEqual(result["total_gross"], 0)

    def test_open_ended_and_single_day_ranges(self):
        for filters in [{"start_date": "2026-08-12"}, {"end_date": "2026-07-10"}, {"start_date": "2026-08-12", "end_date": "2026-08-12"}]:
            with self.subTest(filters=filters):
                result = build_premium_history(LegacyStub, self.operations, **filters)
                self.assertEqual(len(result["rows"]), 1)
                self.assertFalse(result["errors"])

    def test_invalid_filters_never_fall_back_to_all_history(self):
        for filters in [{"start_date": "2026-08-31", "end_date": "2026-08-01"}, {"start_date": "2026-02-30"}, {"selected_month": "2026-13"}, {"selected_year": "oops"}, {"period": "range"}, {"period": "month"}, {"period": "invalid"}]:
            with self.subTest(filters=filters):
                result = build_premium_history(LegacyStub, self.operations, **filters)
                self.assertTrue(result["errors"])
                self.assertEqual(result["rows"], ())
                self.assertEqual(result["total_net"], 0)

    def test_period_switch_ignores_previous_fields_and_legacy_month_links_work(self):
        result = build_premium_history(LegacyStub, self.operations, period="range", selected_month="2026-07", start_date="2026-08-01")
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["asset"], "PETR4")
        month = build_premium_history(LegacyStub, self.operations, selected_month="2026-08", selected_year="2025")
        self.assertEqual(len(month["rows"]), 1)
        all_rows = build_premium_history(LegacyStub, self.operations, period="all", start_date="invalid", selected_month="2026-07")
        self.assertEqual(len(all_rows["rows"]), 2)

    def test_explicit_underlying_is_respected(self):
        operation = dict(self.operations[1], Ativo_subjacente="PETR3")
        result = build_premium_history(LegacyStub, [operation], selected_asset="PETR4")
        self.assertEqual(result["rows"], ())
        self.assertEqual(result["assets"], ("PETR3",))


if __name__ == "__main__":
    unittest.main()
