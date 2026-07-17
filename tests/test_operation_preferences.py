import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from app import app
import legacy_app
from services.operation_preferences_service import (
    apply_operation_preferences,
    delete_operation_preference,
    load_operation_metadata,
    load_operation_preferences,
    save_operation_metadata,
    save_exercise_interest,
)


FIELDS = ["ID", "Data abertura", "Ativo", "Tipo", "Estratégia", "Status", "Contratos", "Strike", "Premio_opcao", "Custos", "IRRF", "Vencimento", "Cotacao_atual", "Resultado_realizado"]


def test_exercise_interest_is_saved_applied_and_deleted():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(legacy_app, "DATA", root), patch.object(legacy_app, "USE_POSTGRES", False):
            assert save_exercise_interest(legacy_app, "7", "sim") is True
            assert load_operation_preferences(legacy_app) == {"7": True}
            operations = [{"ID": "7"}, {"ID": "8"}]
            apply_operation_preferences(operations, legacy_app)
            assert operations == [
                {"ID": "7", "Interesse_exercicio": True},
                {"ID": "8", "Interesse_exercicio": False},
            ]
            delete_operation_preference(legacy_app, "7")
            assert load_operation_preferences(legacy_app) == {}


def test_underlying_asset_is_persisted_without_losing_exercise_interest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch.object(legacy_app, "DATA", root), patch.object(legacy_app, "USE_POSTGRES", False):
            save_operation_metadata(legacy_app, "27", interested=False, underlying_asset="CPLE3")
            assert load_operation_metadata(legacy_app) == {
                "27": {"exercise_interest": False, "underlying_asset": "CPLE3"}
            }
            operations = [{"ID": "27", "Ativo": "CPLES15"}]
            apply_operation_preferences(operations, legacy_app)
            assert operations[0]["Ativo_subjacente"] == "CPLE3"


def test_new_operation_api_persists_exercise_interest():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        operations = root / "operacoes.csv"
        operations.write_text(",".join(FIELDS) + "\n", encoding="utf-8")
        payload = {
            "Ativo": "GOAUS139", "Tipo": "PUT", "Estrategia": "Venda",
            "Contratos": "1", "Strike": "10.21", "Premio_opcao": "0.30",
            "Custos": "0", "IRRF": "0", "Vencimento": "2026-08-21",
            "Cotacao_atual": "10.52", "Interesse_exercicio": True,
            "Ativo_subjacente": "GOAU4",
        }
        with patch.object(legacy_app, "DATA", root), patch.object(legacy_app, "OPERACOES", operations), patch.object(legacy_app, "USE_POSTGRES", False):
            response = app.test_client().post("/api/operacoes", json=payload)
            assert response.status_code == 200
            assert response.get_json()["operation_id"] == "1"
            assert json.loads((root / "operation_preferences.json").read_text(encoding="utf-8")) == {
                "1": {"exercise_interest": True, "underlying_asset": "GOAU4"}
            }
