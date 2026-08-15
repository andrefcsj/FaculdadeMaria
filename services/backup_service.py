"""Backup portátil dos dados operacionais do FaculdadeMaria."""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _postgres_tables(legacy) -> list[dict[str, Any]]:
    if not getattr(legacy, "USE_POSTGRES", False):
        return []
    connection = legacy.get_pg_conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema='public' AND table_type='BASE TABLE'
               ORDER BY table_name"""
        )
        names = [str(row[0]) for row in cursor.fetchall()]
        exports = []
        for name in names:
            cursor.execute(f'SELECT * FROM "{name.replace(chr(34), chr(34) * 2)}"')
            columns = [str(item[0]) for item in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
            exports.append({"table": name, "columns": columns, "rows": rows, "row_count": len(rows)})
        return exports
    finally:
        connection.close()


def build_complete_backup(legacy) -> tuple[io.BytesIO, str, dict[str, Any]]:
    """Cria ZIP com arquivos locais, todas as tabelas públicas e manifesto."""
    generated_at = datetime.now().astimezone()
    data_root = Path(legacy.DATA)
    table_exports = _postgres_tables(legacy)
    manifest: dict[str, Any] = {
        "format": "FaculdadeMaria Portable Backup",
        "format_version": 2,
        "generated_at": generated_at.isoformat(),
        "persistence": "postgresql" if getattr(legacy, "USE_POSTGRES", False) else "local",
        "files": [],
        "database_tables": [],
        "excluded_secrets": [".env", "DATABASE_URL", "SLDX_API_TOKEN", "ADMIN_RESET_PIN"],
    }
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        if data_root.exists():
            for source in sorted(path for path in data_root.rglob("*") if path.is_file()):
                relative = source.relative_to(data_root)
                content = source.read_bytes()
                archive_name = f"files/data/{relative.as_posix()}"
                archive.writestr(archive_name, content)
                manifest["files"].append({
                    "path": archive_name, "bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                })
        for export in table_exports:
            name = export["table"]
            content = json.dumps(export, ensure_ascii=False, indent=2, default=_json_default).encode("utf-8")
            archive_name = f"database/{name}.json"
            archive.writestr(archive_name, content)
            manifest["database_tables"].append({
                "table": name, "rows": export["row_count"], "path": archive_name,
                "sha256": hashlib.sha256(content).hexdigest(),
            })
        readme = (
            "BACKUP COMPLETO DO FACULDADEMARIA\n\n"
            "Conteúdo:\n"
            "- files/data/: cópia dos arquivos persistentes locais;\n"
            "- database/: exportação JSON de todas as tabelas públicas do PostgreSQL/Neon;\n"
            "- manifest.json: inventário, contagens e hashes de integridade.\n\n"
            "Segredos e credenciais não são incluídos. Preserve este arquivo em local seguro.\n"
        )
        archive.writestr("README_BACKUP.txt", readme)
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, default=_json_default),
        )
    memory.seek(0)
    filename = f"Backup_FaculdadeMaria_{generated_at.strftime('%Y-%m-%d_%H-%M-%S')}.zip"
    return memory, filename, manifest
