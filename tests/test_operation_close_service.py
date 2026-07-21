from datetime import date
from decimal import Decimal
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import legacy_app
from services.operation_close_service import calculate_operation_close


class OperationCloseServiceTests(unittest.TestCase):
    def close(self, method, **changes):
        values = dict(
            method=method,
            close_date=date(2026, 7, 11),
            expiry=date(2026, 7, 11),
            premium_received=Decimal("100"),
            repurchase_per_unit=Decimal("0.40"),
            contracts=Decimal("1"),
            contract_size=Decimal("100"),
        )
        values.update(changes)
        return calculate_operation_close(**values)

    def test_repurchase_calculates_final_result(self):
        result = self.close("recompra")
        self.assertEqual(result.repurchase_total, Decimal("40.00"))
        self.assertEqual(result.result, Decimal("60.00"))

    def test_exercise_preserves_received_premium(self):
        result = self.close("exercida")
        self.assertEqual(result.result, Decimal("100"))
        self.assertEqual(result.status, "Encerrada")

    def test_cancel_closes_with_zero_result(self):
        self.assertEqual(self.close("cancelada").result, Decimal("0"))

    def test_expired_preserves_premium_only_after_expiry(self):
        self.assertEqual(self.close("virou_po").result, Decimal("100"))
        with self.assertRaisesRegex(ValueError, "data do vencimento"):
            self.close("virou_po", expiry=date(2026, 7, 12))

    def test_purchased_option_expiring_worthless_is_full_debit_loss(self):
        result = self.close(
            "virou_po", premium_received=Decimal("3.05"), position_side="Compra"
        )
        self.assertEqual(result.result, Decimal("-3.05"))

    def test_purchased_option_sale_subtracts_opening_debit(self):
        result = self.close(
            "recompra", premium_received=Decimal("3.05"),
            repurchase_per_unit=Decimal("0.05"), position_side="Compra",
        )
        self.assertEqual(result.repurchase_total, Decimal("5.00"))
        self.assertEqual(result.result, Decimal("1.95"))

    def test_rejects_unknown_method(self):
        with self.assertRaisesRegex(ValueError, "forma válida"):
            self.close("qualquer")

    def test_route_closes_csv_and_returns_to_open_operations(self):
        fields = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]
        row = dict.fromkeys(fields, "")
        row.update({"ID": "99", "Ativo": "BBDCT20", "Tipo": "PUT", "Estratégia": "Venda", "Status": "Aberta", "Contratos": "1", "Strike": "18.81", "Premio_opcao": "1.00", "Custos": "0", "IRRF": "0", "Vencimento": "2026-08-21", "Resultado_realizado": "0"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operacoes.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader(); writer.writerow(row)
            with patch.object(legacy_app, "DATA", Path(directory)), patch.object(legacy_app, "OPERACOES", path), patch.object(legacy_app, "USE_POSTGRES", False):
                response = legacy_app.app.test_client().post(
                    "/fechar/99",
                    data={"metodo_encerramento": "recompra", "data_encerramento": "2026-07-11", "valor_recompra": "0.40"},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["redirect"], "/operacoes-abertas?encerrada=1")
            saved = list(csv.DictReader(path.open(encoding="utf-8")))[0]
            self.assertEqual(saved["Status"], "Encerrada")
            self.assertEqual(Decimal(saved["Resultado_realizado"]), Decimal("60.0"))
            self.assertTrue((Path(directory) / "operation_closures.json").exists())

    def test_route_records_full_debit_when_purchased_put_expires_worthless(self):
        fields = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]
        row = dict.fromkeys(fields, "")
        row.update({"ID":"129", "Ativo":"CPLES129", "Tipo":"PUT", "Estratégia":"Compra", "Status":"Aberta", "Contratos":"1", "Strike":"12.78", "Premio_opcao":"0.02", "Custos":"1.05", "IRRF":"0", "Vencimento":"2026-07-17", "Resultado_realizado":"0"})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "operacoes.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader(); writer.writerow(row)
            with patch.object(legacy_app, "DATA", Path(directory)), patch.object(legacy_app, "OPERACOES", path), patch.object(legacy_app, "USE_POSTGRES", False):
                response = legacy_app.app.test_client().post(
                    "/fechar/129",
                    data={"metodo_encerramento":"virou_po", "data_encerramento":"2026-07-17", "valor_recompra":"0"},
                    headers={"X-Requested-With":"XMLHttpRequest"},
                )
            self.assertEqual(response.status_code, 200)
            saved = list(csv.DictReader(path.open(encoding="utf-8")))[0]
            self.assertEqual(Decimal(saved["Resultado_realizado"]), Decimal("-3.05"))


if __name__ == "__main__":
    unittest.main()
