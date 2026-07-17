from pathlib import Path


def test_open_operations_has_new_operation_popup_button():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert 'class="new-operation-button"' in template
    assert "data-open-new-operation" in template
    assert "Cadastrar Operação" in template


def test_open_operations_shows_entry_current_price_and_strike_distance():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert "Preço de entrada" in template
    assert "Preço atual" in template
    assert "Distância do strike" in template
    assert "distancia_strike_class" in template
    assert "fonte_preco_atual" in template
    assert "data-manual-quote" in template
    assert "Prazo / status" in template
