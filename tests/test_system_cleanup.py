import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app import app
import legacy_app
from services.system_cleanup_service import execute_cleanup, preview_cleanup


FIELDS=["ID","Data abertura","Ativo","Tipo","Estratégia","Status","Contratos","Strike","Premio_opcao","Custos","IRRF","Vencimento","Cotacao_atual","Resultado_realizado"]


class SystemCleanupTests(unittest.TestCase):
    def environment(self):
        directory=tempfile.TemporaryDirectory();root=Path(directory.name);ops=root/"operacoes.csv";closed=root/"fechadas.csv"
        rows=[]
        for identifier,opened in (("1","2026-06-10"),("2","2026-07-11")):
            row=dict.fromkeys(FIELDS,"");row.update({"ID":identifier,"Data abertura":opened,"Ativo":"BBDCS167","Tipo":"PUT","Estratégia":"Venda","Status":"Aberta","Contratos":"1","Strike":"16.7","Premio_opcao":"0.33","Custos":"1","IRRF":"0","Vencimento":"2026-08-21","Cotacao_atual":"18","Resultado_realizado":"0"});rows.append(row)
        with ops.open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
        with closed.open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=["Mes","Resultado_final"]);writer.writeheader();writer.writerow({"Mes":"Jun/26","Resultado_final":"10"})
        (root/"brokerage_notes.json").write_text(json.dumps([{"operation_id":"1","trade_date":"2026-06-10"},{"operation_id":"2","trade_date":"2026-07-11"}]),encoding="utf-8")
        (root/"operation_closures.json").write_text(json.dumps({"1":{"close_date":"2026-06-20"}}),encoding="utf-8")
        patches=(patch.object(legacy_app,"DATA",root),patch.object(legacy_app,"OPERACOES",ops),patch.object(legacy_app,"FECHADAS",closed),patch.object(legacy_app,"USE_POSTGRES",False))
        return directory,root,ops,patches

    def test_month_cleanup_removes_only_operations_opened_in_month_and_links(self):
        directory,root,ops,patches=self.environment()
        with directory,patches[0],patches[1],patches[2],patches[3]:
            preview=preview_cleanup(legacy_app,scope="month",period="2026-06")
            self.assertEqual((preview.operations,preview.imported_notes,preview.closures),(1,1,1))
            execute_cleanup(legacy_app,scope="month",period="2026-06")
            remaining=list(csv.DictReader(ops.open(encoding="utf-8")))
            self.assertEqual([row["ID"] for row in remaining],["2"])
            notes=json.loads((root/"brokerage_notes.json").read_text())
            self.assertEqual([row["operation_id"] for row in notes],["2"])

    def test_complete_reset_clears_operational_data_but_not_config(self):
        directory,root,ops,patches=self.environment();config=root/"config.csv";config.write_text("Parametro,Valor\nMeta ROI mensal,0.04\n",encoding="utf-8")
        with directory,patches[0],patches[1],patches[2],patches[3]:
            execute_cleanup(legacy_app,scope="all",period="")
            self.assertEqual(list(csv.DictReader(ops.open(encoding="utf-8"))),[])
            self.assertTrue(config.exists())

    def test_destructive_endpoint_requires_configured_pin_and_phrase(self):
        directory,_root,_ops,patches=self.environment()
        with directory,patches[0],patches[1],patches[2],patches[3],patch.dict(os.environ,{"ADMIN_RESET_PIN":"segredo"}):
            client=app.test_client()
            wrong=client.post("/api/configuracoes/limpeza/executar",json={"scope":"all","period":"","pin":"errado","confirmation":"ZERAR FACULDADEMARIA"})
            self.assertEqual(wrong.status_code,400)
            right=client.post("/api/configuracoes/limpeza/executar",json={"scope":"all","period":"","pin":"segredo","confirmation":"ZERAR FACULDADEMARIA"})
            self.assertEqual(right.status_code,200)

    def test_settings_page_is_premium_and_explains_preserved_data(self):
        html=app.test_client().get("/configuracoes").get_data(as_text=True)
        self.assertIn("Central de configurações",html)
        self.assertIn("Zerar ambiente operacional",html)
        self.assertIn("Sempre preservado",html)


if __name__=="__main__":unittest.main()
