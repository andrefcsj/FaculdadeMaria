from pathlib import Path


def test_open_operations_has_new_operation_popup_button():
    template = (Path(__file__).parents[1] / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    assert 'class="new-operation-button"' in template
    assert "data-open-new-operation" in template
    assert "Cadastrar Operação" in template
