import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from services.backup_service import build_complete_backup


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


def test_backup_download_requires_admin_pin(monkeypatch):
    from app import app

    monkeypatch.setenv("ADMIN_RESET_PIN", "senha-segura")
    client = app.test_client()
    assert client.get("/backup-completo").status_code == 405
    assert client.post("/backup-completo", data={"admin_pin": "errada"}).status_code == 403
