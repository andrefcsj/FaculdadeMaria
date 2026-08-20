from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_dashboard_has_api_refresh_copy_and_real_equity_composition():
    template = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    assert "Atualizar opções pela API" in template
    assert 'name="next" value="dashboard"' in template
    assert "data-copy-option" in template
    assert "group_items|sum(attribute='total')" in template
    assert "dashboard.equity_portfolio" in template
    for label in ("Quantidade", "PM fiscal", "PM gerencial"):
        assert label in template


def test_open_operations_uses_api_quote_and_removes_redundant_type_column():
    template = (ROOT / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    header = template[template.index('<table class="premium-ops"'):template.index("</thead>")]
    assert ">Tipo</th>" not in header
    assert "Atualizar Profit" not in template
    assert "Informar Profit" not in template
    assert "Sem cotação na última atualização da API" in template


def test_dashboard_copy_handler_copies_only_option_and_expiry():
    script = (ROOT / "static" / "dashboard.js").read_text(encoding="utf-8")
    assert "navigator.clipboard.writeText(value)" in script
    assert "button.dataset.copyOption" in script
