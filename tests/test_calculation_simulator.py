from pathlib import Path

from app import app


def test_calculation_simulator_has_call_and_put_tabs_on_same_screen():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert b'Simulador de CALL' in response.data
    assert b'Simulador de PUT' in response.data
    assert b'data-calculation-panel="call"' in response.data
    assert b'data-calculation-panel="put"' in response.data


def test_put_simulator_covers_assignment_with_and_without_existing_shares():
    html = (Path(__file__).parents[1] / "templates" / "components" / "calculation_simulator_modal.html").read_text(encoding="utf-8")
    for label in (
        "Quantidade atual em carteira", "Preço médio atual", "Contratos de PUT vendidos",
        "PM líquido da compra", "PM após o exercício", "PM se a PUT expirar",
    ):
        assert label in html


def test_put_simulator_combines_current_position_and_assignment_cost():
    script = (Path(__file__).parents[1] / "static" / "calculation_simulator.js").read_text(encoding="utf-8")
    assert "currentAverage*currentQuantity" in script
    assert "+requiredCapital-netPremium" in script
    assert "currentAverage-netPremium/currentQuantity" in script
