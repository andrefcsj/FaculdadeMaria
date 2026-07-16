from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_requested_financial_pages_load_readability_styles():
    for name in ("operacoes_fechadas.html", "novos_aportes.html", "notas_importadas.html", "darfs_pagos.html"):
        template = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert "page_readability.css" in template


def test_readability_styles_raise_table_and_caption_sizes():
    css = (ROOT / "static" / "page_readability.css").read_text(encoding="utf-8")
    assert ".closed-table td{font-size:14px" in css
    assert ".finance-table-wrap td{font-size:14px" in css
    assert ".notes-table td{font-size:14px" in css
