from pathlib import Path


def test_close_modal_calculates_retained_premium_percentage_from_unit_values():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "operacoes_abertas.html").read_text(encoding="utf-8")
    script = (root / "static" / "op_abertas.js").read_text(encoding="utf-8")

    assert 'data-premium-unit="{{ o.Premio_opcao_n }}"' in template
    assert 'id="closeProfitPercent"' in template
    assert "((premiumUnit-Number(repurchase.value||0))/premiumUnit)*100" in script
    assert "minimumFractionDigits:2" in script
