import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app
import legacy_app
from services.closed_operations_service import build_closed_dashboard, save_closure_metadata, serialize_closed_operation


FIELDS = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]


class ClosedOperationsTests(unittest.TestCase):
    def environment(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        operations = root / "operacoes.csv"
        row = dict.fromkeys(FIELDS, "")
        row.update({"ID":"7","Data abertura":"2026-06-10","Ativo":"BBDCS167","Tipo":"PUT","Estratégia":"Venda","Status":"Encerrada","Contratos":"1","Strike":"16.70","Premio_opcao":"0.33","Custos":"1.08","IRRF":"0","Vencimento":"2026-07-17","Cotacao_atual":"18","Resultado_realizado":"20"})
        with operations.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS); writer.writeheader(); writer.writerow(row)
        patches = (patch.object(legacy_app,"DATA",root),patch.object(legacy_app,"OPERACOES",operations),patch.object(legacy_app,"USE_POSTGRES",False))
        return directory, root, operations, patches

    def test_dashboard_filters_closed_operations_by_current_month(self):
        directory, _root, _operations, patches = self.environment()
        with directory, patches[0], patches[1], patches[2]:
            save_closure_metadata(legacy_app,"7",close_date=date.today(),method="recompra",repurchase_value=Decimal("0.13"),result=Decimal("20"))
            dashboard = build_closed_dashboard(legacy_app,scope="current",selected_month="")
            self.assertEqual(dashboard["selected_count"],1)
            self.assertEqual(dashboard["month_profit"],Decimal("20"))

    def test_page_has_cards_filters_and_three_actions(self):
        html = app.test_client().get("/operacoes-fechadas").get_data(as_text=True)
        for label in ("Lucro do mês","Lucro acumulado","ROI médio","Total de operações","Mês atual","Ano atual","Mês específico"):
            self.assertIn(label,html)
        self.assertIn('id="closedEditModal"',html)
        script=Path("static/closed_operations.js").read_text(encoding="utf-8")
        self.assertIn("data-closed-edit",script)
        self.assertIn("data-closed-delete",script)
        self.assertIn("data-closed-reopen",script)

    def test_closed_table_has_requested_column_order_without_costs(self):
        template = Path("templates/operacoes_fechadas.html").read_text(encoding="utf-8")
        headers = ["Ação", "Código da opção", "Resultado", "ROI", "Abertura e fechamento", "Strike", "Encerramento", "Posição", "Ações"]
        positions = [template.index(f">{header}</th>") for header in headers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn(">Custos / IRRF</th>", template)
        self.assertIn("closed-asset-logo", template)

    def test_serialized_operation_contains_underlying_logo(self):
        directory, _root, _operations, patches = self.environment()
        with directory, patches[0], patches[1], patches[2]:
            operation = legacy_app.read_csv(legacy_app.OPERACOES)[0]
            serialized = serialize_closed_operation(legacy_app, operation)
            self.assertEqual(serialized["Ativo_subjacente"], "BBDC4")
            self.assertEqual(serialized["Logo_subjacente"], "https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/BBDC4.png")

    def test_reopen_returns_operation_to_open_list_and_clears_result(self):
        directory, _root, operations, patches = self.environment()
        with directory, patches[0], patches[1], patches[2]:
            save_closure_metadata(legacy_app,"7",close_date=date.today(),method="recompra",repurchase_value=Decimal("0.13"),result=Decimal("20"))
            response = app.test_client().post("/api/operacoes-fechadas/7/reabrir")
            self.assertEqual(response.status_code,200)
            saved=list(csv.DictReader(operations.open(encoding="utf-8")))[0]
            self.assertEqual(saved["Status"],"Aberta")
            self.assertEqual(saved["Resultado_realizado"],"0")

    def test_edit_closed_operation_stays_closed(self):
        directory, _root, operations, patches = self.environment()
        with directory, patches[0], patches[1], patches[2]:
            payload={"Ativo":"BBDCS167","Tipo":"PUT","Estrategia":"Venda","Contratos":"1","Strike":"16.70","Premio_opcao":"0.33","Custos":"1.08","IRRF":"0","Vencimento":"2026-07-17","Cotacao_atual":"18","Data_fechamento":date.today().isoformat(),"Resultado_realizado":"21.50","Metodo_encerramento":"recompra","Valor_recompra":"0.11"}
            response=app.test_client().post("/api/operacoes-fechadas/7",json=payload)
            self.assertEqual(response.status_code,200)
            saved=list(csv.DictReader(operations.open(encoding="utf-8")))[0]
            self.assertEqual(saved["Status"],"Encerrada")
            self.assertEqual(saved["Resultado_realizado"],"21.50")

    def test_sidebar_contains_open_and_closed_operations(self):
        html=app.test_client().get("/").get_data(as_text=True)
        self.assertIn("Operações Abertas",html)
        self.assertIn("Operações Fechadas",html)
        self.assertNotIn("Carteira de PUTs",html)


if __name__ == "__main__": unittest.main()
