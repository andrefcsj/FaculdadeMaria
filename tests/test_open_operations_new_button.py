from pathlib import Path


def test_open_operations_has_new_operation_popup_button():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert 'class="new-operation-button"' in template
    assert "data-open-new-operation" in template
    assert "Cadastrar Operação" in template


def test_open_operations_shows_premium_strike_and_distance_without_option_current_price():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert "Valor do prêmio" in template
    assert "<th>Opção</th><th>Strike</th><th>Valor do prêmio</th>" in template
    assert "<th>Preço atual</th>" not in template
    assert "Distância do strike" in template
    assert "distancia_strike_class" in template
    assert "Prazo / status" in template
