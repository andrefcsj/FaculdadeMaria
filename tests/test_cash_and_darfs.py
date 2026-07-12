import json
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app
import legacy_app
from services.cash_ledger_service import calculate_broker_balance,save_cash_event
from services.paid_darf_service import build_darf_dashboard,save_paid_darf


class CashAndDarfTests(unittest.TestCase):
    def environment(self):
        directory=tempfile.TemporaryDirectory();root=Path(directory.name)
        patches=(patch.object(legacy_app,"DATA",root),patch.object(legacy_app,"USE_POSTGRES",False),patch.object(legacy_app,"OPERACOES",root/"operacoes.csv"),patch.object(legacy_app,"FECHADAS",root/"fechadas.csv"))
        (root/"operacoes.csv").write_text("ID,Data abertura,Ativo,Tipo,Estratégia,Status,Contratos,Strike,Premio_opcao,Custos,IRRF,Vencimento,Cotacao_atual,Resultado_realizado\n",encoding="utf-8")
        (root/"fechadas.csv").write_text("Mes\n",encoding="utf-8")
        return directory,root,patches

    def test_contribution_and_withdrawal_recalculate_broker_balance(self):
        directory,_root,patches=self.environment()
        with directory,patches[0],patches[1],patches[2],patches[3]:
            save_cash_event(legacy_app,kind="aporte",amount=Decimal("1000"),event_date=date.today(),description="Aporte")
            save_cash_event(legacy_app,kind="retirada",amount=Decimal("125"),event_date=date.today(),description="Saque")
            summary=calculate_broker_balance(legacy_app)
            self.assertEqual(summary["balance"],Decimal("875"))

    def test_paid_darf_can_be_manual_without_demo_pdf(self):
        directory,_root,patches=self.environment()
        with directory,patches[0],patches[1],patches[2],patches[3]:
            save_paid_darf(legacy_app,competence="2026-07",payment_date=date(2026,8,31),due_date=None,revenue_code="6015",amount=Decimal("42.50"),description="Pagamento manual",pdf=None)
            dashboard=build_darf_dashboard(legacy_app,scope="month",month="2026-07",year="")
            self.assertEqual(dashboard["count"],1)
            self.assertEqual(dashboard["total_all"],Decimal("42.50"))

    def test_note_credit_is_not_duplicated_but_later_repurchase_is_debited(self):
        directory,root,patches=self.environment()
        with directory,patches[0],patches[1],patches[2],patches[3]:
            (root/"operacoes.csv").write_text("ID,Data abertura,Ativo,Tipo,Estratégia,Status,Contratos,Strike,Premio_opcao,Custos,IRRF,Vencimento,Cotacao_atual,Resultado_realizado\n1,2026-07-01,BBDCS167,PUT,Venda,Encerrada,1,16.70,0.33,1.08,0,2026-07-17,18,21.92\n",encoding="utf-8")
            (root/"brokerage_notes.json").write_text(json.dumps([{"key":"hash:0","operation_id":"1","trade_date":"2026-07-01","cash_direction":"C","net_cash":"31.92","note_number":"1","trade":{"option_code":"BBDCS167"}}]),encoding="utf-8")
            (root/"operation_closures.json").write_text(json.dumps({"1":{"close_date":"2026-07-10","method":"recompra","repurchase_value":"0.10"}}),encoding="utf-8")
            summary=calculate_broker_balance(legacy_app)
            self.assertEqual(summary["balance"],Decimal("21.92"))

    def test_paid_darf_pdf_is_not_stored_and_duplicate_is_blocked(self):
        directory,root,patches=self.environment();pdf=b"%PDF-1.4\nfixture"
        with directory,patches[0],patches[1],patches[2],patches[3]:
            save_paid_darf(legacy_app,competence="2026-07",payment_date=date.today(),due_date=None,revenue_code="6015",amount=Decimal("10"),description="",pdf=pdf)
            with self.assertRaisesRegex(ValueError,"já foi cadastrado"):
                save_paid_darf(legacy_app,competence="2026-07",payment_date=date.today(),due_date=None,revenue_code="6015",amount=Decimal("10"),description="",pdf=pdf)
            self.assertFalse(any(path.suffix==".pdf" for path in root.iterdir()))

    def test_pages_and_menu_are_available(self):
        client=app.test_client()
        self.assertEqual(client.get("/novos-aportes").status_code,200)
        self.assertEqual(client.get("/darfs-pagos").status_code,200)
        html=client.get("/").get_data(as_text=True)
        self.assertLess(html.index("Cadastrar Operação"),html.index("Operações Abertas"))
        self.assertIn("Novos Aportes",html);self.assertIn("DARFs Pagos",html)


if __name__=="__main__":unittest.main()
