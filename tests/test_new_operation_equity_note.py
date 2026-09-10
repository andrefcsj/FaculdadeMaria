from decimal import Decimal
from unittest.mock import patch

import pytest
import legacy_app
from app import app
from services.brokerage_note_service import note_to_api, parse_btg_necton_pdf, load_imported_notes
from services.equity_position_service import manual_equity_lot, save_equity_lot, portfolio
from test_covered_call_and_assignment import EQUITY_SALE_TEXT, EQUITY_PURCHASE_TEXT


@pytest.fixture
def isolated_portfolio(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy_app, 'DATA', tmp_path)
    monkeypatch.setattr(legacy_app, 'OPERACOES', tmp_path / 'operacoes.csv')
    monkeypatch.setattr(legacy_app, 'USE_POSTGRES', False)
    return app.test_client()


def parsed_note(text):
    with patch('services.brokerage_note_service.extract_pdf_text', return_value=text):
        note = note_to_api(parse_btg_necton_pdf(text.encode()))
    return {**note, 'trade': note['trades'][0]}


def test_new_operation_registers_lftb_sale_without_option_fields(isolated_portfolio):
    save_equity_lot(legacy_app, manual_equity_lot(
        asset='LFTB11', quantity=50, average_price=Decimal('50'), acquisition_date='2026-07-01'))
    note = parsed_note(EQUITY_SALE_TEXT)
    payload = {'Ativo': 'LFTB11', 'Nota_corretagem': note}
    response = isolated_portfolio.post('/api/operacoes', json=payload)
    assert response.status_code == 200, response.get_json()
    assert response.json['sales'][0]['quantity'] == 37
    assert Decimal(response.json['sales'][0]['net_proceeds']) == Decimal('2070.50')
    assert portfolio(legacy_app)[0]['quantity'] == 13
    assert legacy_app.read_csv(legacy_app.OPERACOES) == []
    assert len(load_imported_notes(legacy_app)) == 1
    assert isolated_portfolio.post('/api/operacoes', json=payload).status_code == 400
    assert portfolio(legacy_app)[0]['quantity'] == 13


def test_new_operation_registers_equity_purchase_without_strike_or_expiry(isolated_portfolio):
    note = parsed_note(EQUITY_PURCHASE_TEXT)
    response = isolated_portfolio.post('/api/operacoes', json={'Ativo': 'CPLE3', 'Nota_corretagem': note})
    assert response.status_code == 200, response.get_json()
    holding = portfolio(legacy_app)[0]
    assert holding['asset'] == 'CPLE3'
    assert holding['quantity'] == 100
    assert holding['tax_cost_total'] == 1471.5
    assert legacy_app.read_csv(legacy_app.OPERACOES) == []


def test_equity_sale_without_holdings_changes_nothing(isolated_portfolio):
    response = isolated_portfolio.post('/api/operacoes', json={
        'Ativo': 'LFTB11', 'Nota_corretagem': parsed_note(EQUITY_SALE_TEXT)})
    assert response.status_code == 400
    assert 'livres' in response.json['error']
    assert load_imported_notes(legacy_app) == []


def test_options_still_require_strike(isolated_portfolio):
    response = isolated_portfolio.post('/api/operacoes', json={
        'Ativo': 'PETRT480', 'Tipo': 'PUT', 'Estrategia': 'Venda',
        'Vencimento': '2026-09-18', 'Contratos': '1', 'Premio_opcao': '0.5'})
    assert response.status_code == 400
    assert 'Strike' in response.json['error']
