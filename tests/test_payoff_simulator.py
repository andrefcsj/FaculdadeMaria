from app import app


def test_payoff_simulator_page_has_comparison_and_single_asset_controls():
    response = app.test_client().get("/estrategias/simulador-payoff")

    assert response.status_code == 200
    assert b"Simulador de Payoff" in response.data
    assert b"Ativo da estrat" in response.data
    assert b"Somente venda da PUT" in response.data
    assert b"Diferen" in response.data
    assert b"payoffChart" in response.data
    assert b"payoffTooltip" in response.data
    assert b"Quantidade" in response.data
    assert b"Dist" in response.data
    assert b">ROI<" in response.data
    assert b"payoffFloatingTooltip" in response.data
    assert b"BE Jade" in response.data
    assert b"BE PUT" in response.data
    assert b"payoff_simulator.js" in response.data


def test_navigation_exposes_both_strategy_modules():
    response = app.test_client().get("/estrategias/simulador-payoff")

    assert b"/estrategias/jade-lizard" in response.data
    assert b"/estrategias/simulador-payoff" in response.data
