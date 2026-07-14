import json
from decimal import Decimal
from pathlib import Path
import tempfile
from unittest.mock import patch

from app import app
import legacy_app


FIELDS = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]


def test_confirmed_purchase_note_closes_matching_open_sale():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        operations = root / "operacoes.csv"
        operations.write_text(
            ",".join(FIELDS) + "\n1,2026-07-10,CPLES15,PUT,Venda,Aberta,1,10.00,0.33,0,0,2026-08-21,11,0\n",
            encoding="utf-8",
        )
        note = {
            "document_hash": "closing-hash", "note_number": "99", "trade_date": "2026-07-11",
            "broker": "BTG Pactual / Necton", "cash_direction": "D", "net_cash": "6.50",
            "operational_costs": "0.50", "irrf": "0", "gross_operations": "6.00",
            "trade": {"trade_index": 0, "option_code": "CPLES15", "side": "Compra", "quantity": 100, "unit_price": "0.06", "allocated_costs": "0.50", "allocated_irrf": "0"},
        }
        with patch.object(legacy_app, "DATA", root), patch.object(legacy_app, "OPERACOES", operations), patch.object(legacy_app, "USE_POSTGRES", False):
            response = app.test_client().post("/api/operacoes", json={"Ativo": "CPLES15", "Nota_corretagem": note, "Encerrar_operacao_id": "1"})

            assert response.status_code == 200
            assert response.get_json()["closed"] is True
            rows = legacy_app.read_csv(operations)
            assert rows[0]["Status"] == "Encerrada"
            assert Decimal(rows[0]["Resultado_realizado"]) == Decimal("26.50")
            saved = json.loads((root / "brokerage_notes.json").read_text(encoding="utf-8"))
            assert len(saved) == 1


def test_partial_purchase_note_is_rejected_by_automatic_close():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory);operations = root / "operacoes.csv"
        operations.write_text(",".join(FIELDS) + "\n1,2026-07-10,CPLES15,PUT,Venda,Aberta,1,10.00,0.33,0,0,2026-08-21,11,0\n", encoding="utf-8")
        note = {"document_hash":"partial","trade_date":"2026-07-11","trade":{"trade_index":0,"option_code":"CPLES15","side":"Compra","quantity":50,"unit_price":"0.06"}}
        with patch.object(legacy_app,"DATA",root),patch.object(legacy_app,"OPERACOES",operations),patch.object(legacy_app,"USE_POSTGRES",False):
            response=app.test_client().post("/api/operacoes",json={"Ativo":"CPLES15","Nota_corretagem":note,"Encerrar_operacao_id":"1"})
            assert response.status_code == 400
            assert "parcial" in response.get_json()["error"].lower()


def test_mixed_note_can_close_one_trade_and_open_the_other():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory);operations = root / "operacoes.csv"
        operations.write_text(",".join(FIELDS) + "\n1,2026-06-10,BBDCS167,PUT,Venda,Aberta,1,16.89,0.33,0,0,2026-07-17,18.77,0\n", encoding="utf-8")
        common = {
            "document_hash":"mixed-note", "note_number":"32813199", "trade_date":"2026-06-29",
            "broker":"BTG Pactual / Necton", "cash_direction":"C", "net_cash":"35.84",
            "operational_costs":"2.16", "irrf":"0", "gross_operations":"50.00",
        }
        closing_trade = {"trade_index":0,"option_code":"BBDCS167","side":"Compra","quantity":100,"contracts":"1","unit_price":"0.06","gross_value":"6.00","cash_direction":"D","allocated_costs":"0.26","allocated_irrf":"0"}
        opening_trade = {"trade_index":1,"option_code":"BBDCS183","side":"Venda","quantity":100,"contracts":"1","unit_price":"0.44","gross_value":"44.00","cash_direction":"C","allocated_costs":"1.90","allocated_irrf":"0"}
        with patch.object(legacy_app,"DATA",root),patch.object(legacy_app,"OPERACOES",operations),patch.object(legacy_app,"USE_POSTGRES",False):
            client = app.test_client()
            close_response = client.post("/api/operacoes", json={"Ativo":"BBDCS167","Nota_corretagem":{**common,"trade":closing_trade,"trades":[closing_trade,opening_trade]},"Encerrar_operacao_id":"1"})
            assert close_response.status_code == 200
            open_response = client.post("/api/operacoes", json={
                "Ativo":"BBDCS183","Tipo":"PUT","Estrategia":"Venda","Contratos":"1","Strike":"18.30",
                "Premio_opcao":"0.44","Custos":"1.90","IRRF":"0","Vencimento":"2026-07-17","Cotacao_atual":"18.77",
                "Nota_corretagem":{**common,"trade":opening_trade,"trades":[closing_trade,opening_trade]},
            })
            assert open_response.status_code == 200
            rows = legacy_app.read_csv(operations)
            assert len(rows) == 2
            assert rows[0]["Status"] == "Encerrada"
            assert rows[1]["Ativo"] == "BBDCS183"
            assert rows[1]["Status"] == "Aberta"
            saved = json.loads((root / "brokerage_notes.json").read_text(encoding="utf-8"))
            assert [item["key"] for item in saved] == ["mixed-note:0", "mixed-note:1"]
