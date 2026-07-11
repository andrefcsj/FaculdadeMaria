from datetime import date
from pathlib import Path

import pytest

from services.market_import_service import (
    MarketImportError,
    load_market_import,
    parse_market_csv,
    save_market_import,
)


def test_importa_csv_com_aliases_em_portugues(tmp_path: Path):
    csv_data = (
        "Opção;Ativo;Tipo;Vencimento;Cotação Ativo;Strike;Prêmio;Bid;Ask;Volume\n"
        "PETRT380;PETR4;PUT;21/08/2026;40,00;38,00;1,26;1,20;1,30;25000\n"
    ).encode("utf-8")

    result = parse_market_csv(csv_data, as_of=date(2026, 7, 11))

    assert result.accepted_rows == 1
    assert result.rejected_rows == 0
    opportunity = result.opportunities[0]
    assert opportunity.asset == "PETR4"
    assert opportunity.option_code == "PETRT380"
    assert str(opportunity.strike) == "38.00"
    assert str(opportunity.premium) == "1.26"
    assert opportunity.expiry == date(2026, 8, 21)

    target = tmp_path / "imported_options.json"
    save_market_import(target, result)
    loaded = load_market_import(target)
    assert loaded is not None
    assert loaded.accepted_rows == 1
    assert loaded.opportunities[0].option_code == "PETRT380"


def test_ignora_call_e_opcao_vencida():
    csv_data = (
        "option_code,asset,option_type,expiry,spot_price,strike,premium\n"
        "PETRA400,PETR4,CALL,2026-08-21,40.00,40.00,1.00\n"
        "PETRQ300,PETR4,PUT,2026-06-20,40.00,30.00,0.50\n"
        "PETRT380,PETR4,PUT,2026-08-21,40.00,38.00,1.26\n"
    ).encode("utf-8")

    result = parse_market_csv(csv_data, as_of=date(2026, 7, 11))

    assert result.accepted_rows == 1
    assert result.rejected_rows == 2
    assert result.opportunities[0].option_code == "PETRT380"


def test_rejeita_csv_sem_colunas_obrigatorias():
    csv_data = b"ativo;strike;premio\nPETR4;38;1,26\n"

    with pytest.raises(MarketImportError, match="Colunas obrigatórias ausentes"):
        parse_market_csv(csv_data, as_of=date(2026, 7, 11))


def test_rejeita_csv_sem_put_valida():
    csv_data = (
        "option_code,asset,option_type,expiry,spot_price,strike,premium\n"
        "PETRA400,PETR4,CALL,2026-08-21,40.00,40.00,1.00\n"
    ).encode("utf-8")

    with pytest.raises(MarketImportError, match="Nenhuma PUT válida"):
        parse_market_csv(csv_data, as_of=date(2026, 7, 11))
