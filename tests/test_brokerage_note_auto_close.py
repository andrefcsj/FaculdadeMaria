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
