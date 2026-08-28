from datetime import date
from decimal import Decimal
from pathlib import Path
from services.live_spot_service import with_current_underlying_quotes
from services.dashboard_service import build_dashboard_view_model, _is_in_the_money
from services.exercise_probability_service import estimate_operation_exercise_probability


def test_petr_weekly_uses_live_spot_in_alert_and_probability(monkeypatch):
    class Legacy:
        infer_acao_from_option = staticmethod(lambda code: 'PETR4')
    operation = dict(Ativo='PETRT426W4', Ativo_subjacente='PETR4', Tipo='PUT',
                     Status='Aberta', Cotacao_n=41.33, Strike_n=41.42,
                     Vencimento='2026-08-28', Dias=0, Interesse_exercicio=True)
    monkeypatch.setattr('services.live_spot_service.fetch_stock_price', lambda ticker: 42.70)
    monkeypatch.setattr('services.exercise_probability_service._fetch_yahoo_history',
                        lambda ticker: (Decimal('41.00'), tuple(Decimal('40') + Decimal(i % 3) for i in range(40))))
    enriched = with_current_underlying_quotes(Legacy, [operation])
    view = build_dashboard_view_model(enriched, [], {}, [], {})
    assert not any(item['option_code'] == 'PETRT426W4' for item in view.attention_items)
    assert view.today_scenario[0]['situation'] == 'Não seria exercida'
    assert view.today_scenario[0]['exercise_probability'] == '0,0%'
    assert operation['Cotacao_n'] == 41.33


def test_equal_strike_is_not_in_the_money():
    for kind in ('PUT', 'CALL'):
        assert not _is_in_the_money(dict(Tipo=kind, Cotacao_n=41.42, Strike_n=41.42))


def test_no_current_quote_does_not_use_history_spot(monkeypatch):
    def unexpected(ticker):
        raise AssertionError('Não deve buscar outra cotação')
    monkeypatch.setattr('services.exercise_probability_service._fetch_yahoo_history', unexpected)
    result = estimate_operation_exercise_probability(ticker='PETR4', option_type='PUT',
        strike=Decimal('41.42'), expiry=date(2026, 8, 28), spot_price=Decimal('0'))
    assert result.probability is None


def test_quick_roi_menu_and_registration_stays_in_open_operations():
    root = Path(__file__).parents[1]
    base = (root / 'templates/base.html').read_text()
    assert base.index('data-open-quick-roi') < base.index('Grade de opções')
    assert 'Cadastrar Operação</a>' not in base
    assert 'components/new_operation_modal.html' in base
    assert 'components/quick_roi_modal.html' in base
