from pathlib import Path


def test_brokerage_import_triggers_immediate_option_lookup():
    root = Path(__file__).resolve().parents[1]
    importer = (root / "static" / "brokerage_note_import.js").read_text(encoding="utf-8")
    lookup = (root / "static" / "new_operation_note_lookup.js").read_text(encoding="utf-8")
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")

    assert "brokerage-trade-applied" in importer
    assert "/api/opcoes/" in lookup
    assert "newStrike" in lookup
    assert "newExpiry" in lookup
    assert "new_operation_note_lookup.js" in base
