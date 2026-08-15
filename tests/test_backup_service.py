import json
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pytest

from services.backup_service import (
    BackupValidationError,
    build_complete_backup,
    inspect_complete_backup,
    restore_complete_backup,
)


def test_complete_local_backup_includes_every_data_file_and_manifest():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "market").mkdir()
        (root / "operacoes.csv").write_text("ID,Ativo\n1,PETR4\n", encoding="utf-8")
        (root / "market" / "imported_options.json").write_text('{"ok": true}', encoding="utf-8")

        class Legacy:
            DATA = root
            USE_POSTGRES = False

        memory, filename, manifest = build_complete_backup(Legacy)
        with ZipFile(memory) as archive:
            names = set(archive.namelist())
            stored_manifest = json.loads(archive.read("manifest.json"))

        assert filename.startswith("Backup_FaculdadeMaria_")
        assert "files/data/operacoes.csv" in names
        assert "files/data/market/imported_options.json" in names
        assert "README_BACKUP.txt" in names
        assert stored_manifest["format_version"] == 2
        assert stored_manifest["persistence"] == "local"
        assert len(manifest["files"]) == 2


def test_complete_postgres_backup_exports_all_public_tables(monkeypatch):
    class Cursor:
        description = []

        def execute(self, statement):
            self.statement = statement
            if "information_schema.tables" not in statement:
                self.description = [("id",), ("payload",)]

        def fetchall(self):
            if "information_schema.tables" in self.statement:
                return [("brokerage_notes",), ("equity_lots",)]
            return [("1", {"asset": "PETR4"})]

    class Connection:
        def __init__(self): self.cursor_value = Cursor(); self.closed = False
        def cursor(self): return self.cursor_value
        def close(self): self.closed = True

    with TemporaryDirectory() as directory:
        connection = Connection()

        class Legacy:
            DATA = Path(directory)
            USE_POSTGRES = True
            get_pg_conn = staticmethod(lambda: connection)

        memory, _filename, manifest = build_complete_backup(Legacy)
        with ZipFile(memory) as archive:
            names = set(archive.namelist())
            exported = json.loads(archive.read("database/equity_lots.json"))

        assert "database/brokerage_notes.json" in names
        assert "database/equity_lots.json" in names
        assert exported["row_count"] == 1
        assert exported["rows"][0]["payload"]["asset"] == "PETR4"
        assert {item["table"] for item in manifest["database_tables"]} == {"brokerage_notes", "equity_lots"}
        assert connection.closed is True


def test_backup_download_does_not_require_admin_pin(monkeypatch):
    from app import app

    client = app.test_client()
    assert client.get("/backup-completo").status_code == 200


def test_complete_local_backup_can_be_validated_and_restored():
    with TemporaryDirectory() as source_directory, TemporaryDirectory() as target_directory:
        source = Path(source_directory)
        target = Path(target_directory)
        (source / "market").mkdir()
        (source / "operacoes.csv").write_text("ID,Ativo\n1,PETR4\n", encoding="utf-8")
        (source / "market" / "quotes.json").write_text('{"PETR4": 31.5}', encoding="utf-8")

        class Source:
            DATA = source
            USE_POSTGRES = False

        class Target:
            DATA = target
            USE_POSTGRES = False

        memory, _filename, _manifest = build_complete_backup(Source)
        result = restore_complete_backup(Target, memory.getvalue())

        assert result["files"] == 2
        assert (target / "operacoes.csv").read_text(encoding="utf-8") == "ID,Ativo\n1,PETR4\n"
        assert (target / "market" / "quotes.json").read_text(encoding="utf-8") == '{"PETR4": 31.5}'


def test_restore_rejects_a_tampered_backup_before_writing_files():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "operacoes.csv").write_text("original", encoding="utf-8")

        class Legacy:
            DATA = root
            USE_POSTGRES = False

        memory, _filename, _manifest = build_complete_backup(Legacy)
        rebuilt = io.BytesIO()
        with ZipFile(memory) as source, ZipFile(rebuilt, "w") as target:
            for item in source.infolist():
                content = source.read(item.filename)
                if item.filename == "files/data/operacoes.csv":
                    content = b"alterado"
                target.writestr(item, content)

        with pytest.raises(BackupValidationError, match="integridade"):
            inspect_complete_backup(rebuilt.getvalue())
        assert (root / "operacoes.csv").read_text(encoding="utf-8") == "original"


def test_restore_endpoint_requires_a_valid_zip():
    from app import app

    client = app.test_client()
    response = client.post(
        "/restaurar-backup",
        data={"backup_file": (io.BytesIO(b"nao e zip"), "backup.zip")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_backup_center_has_download_restore_and_confirmation_ui():
    from app import app

    response = app.test_client().get("/backup")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Criar backup completo" in html
    assert "Restaurar seus dados" in html
    assert "Não abra nem descompacte" in html
    assert "Um ZIP restaura tudo" in html
    assert 'id="restoreModal"' in html


def test_favicon_uses_the_faculdade_maria_academic_brand():
    root = Path(__file__).parents[1]
    favicon = (root / "static" / "favicon.svg").read_text(encoding="utf-8")
    base = (root / "templates" / "base.html").read_text(encoding="utf-8")
    assert "FaculdadeMaria" in favicon
    assert "M10 25.5 32 15l22 10.5" in favicon
    assert "🧠" not in favicon
    assert "20260815.2" in base


def test_wrong_admin_password_has_elegant_recovery_popup():
    root = Path(__file__).parents[1]
    template = (root / "templates" / "configuracoes.html").read_text(encoding="utf-8")
    script = (root / "static" / "settings_cleanup.js").read_text(encoding="utf-8")
    assert 'id="passwordErrorModal"' in template
    assert "Senha administrativa incorreta" in template
    assert "https://dashboard.render.com/" in template
    assert "passwordErrorModal.hidden=false" in script
