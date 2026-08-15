"""Backup portátil dos dados operacionais do FaculdadeMaria."""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


MAX_BACKUP_BYTES = 100 * 1024 * 1024
BACKUP_FORMAT = "FaculdadeMaria Portable Backup"
BACKUP_VERSION = 2


class BackupValidationError(ValueError):
    """Arquivo recusado antes que qualquer dado seja modificado."""


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
        "format": BACKUP_FORMAT,
        "format_version": BACKUP_VERSION,
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


def _safe_json(archive: zipfile.ZipFile, name: str) -> Any:
    try:
        return json.loads(archive.read(name))
    except KeyError as exc:
        raise BackupValidationError(f"O arquivo obrigatório {name} não foi encontrado.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupValidationError(f"O arquivo {name} está corrompido.") from exc


def inspect_complete_backup(upload: bytes) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, bytes]]:
    """Valida completamente o ZIP sem modificar arquivos ou banco de dados."""
    if not upload:
        raise BackupValidationError("Selecione um arquivo de backup.")
    if len(upload) > MAX_BACKUP_BYTES:
        raise BackupValidationError("O backup ultrapassa o limite de 100 MB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(upload))
    except zipfile.BadZipFile as exc:
        raise BackupValidationError("O arquivo selecionado não é um backup ZIP válido.") from exc

    with archive:
        bad_member = archive.testzip()
        if bad_member:
            raise BackupValidationError(f"O item {bad_member} está corrompido.")
        names = set(archive.namelist())
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise BackupValidationError("O ZIP contém caminhos inseguros.")
        manifest = _safe_json(archive, "manifest.json")
        if manifest.get("format") != BACKUP_FORMAT or manifest.get("format_version") != BACKUP_VERSION:
            raise BackupValidationError("Este arquivo não foi criado por uma versão compatível do FaculdadeMaria.")

        tables: dict[str, dict[str, Any]] = {}
        for item in manifest.get("database_tables", []):
            name, path = str(item.get("table", "")), str(item.get("path", ""))
            if not name or path != f"database/{name}.json" or path not in names:
                raise BackupValidationError("O inventário das tabelas está incompleto.")
            content = archive.read(path)
            if hashlib.sha256(content).hexdigest() != item.get("sha256"):
                raise BackupValidationError(f"A tabela {name} falhou na verificação de integridade.")
            export = _safe_json(archive, path)
            if export.get("table") != name or not isinstance(export.get("rows"), list):
                raise BackupValidationError(f"Os dados da tabela {name} são inválidos.")
            if export.get("row_count") != len(export["rows"]):
                raise BackupValidationError(f"A contagem da tabela {name} não confere.")
            tables[name] = export

        files: dict[str, bytes] = {}
        for item in manifest.get("files", []):
            path = str(item.get("path", ""))
            if not path.startswith("files/data/") or path not in names:
                raise BackupValidationError("O inventário dos arquivos locais está incompleto.")
            content = archive.read(path)
            if hashlib.sha256(content).hexdigest() != item.get("sha256"):
                raise BackupValidationError(f"O arquivo {path} falhou na verificação de integridade.")
            files[path.removeprefix("files/data/")] = content
        return manifest, tables, files


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _restore_postgres(legacy, tables: dict[str, dict[str, Any]]) -> int:
    connection = legacy.get_pg_conn()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema='public' AND table_type='BASE TABLE'"""
        )
        current = {str(row[0]) for row in cursor.fetchall()}
        supplied = set(tables)
        if supplied != current:
            missing = sorted(current - supplied)
            unknown = sorted(supplied - current)
            detail = []
            if missing:
                detail.append("faltam: " + ", ".join(missing))
            if unknown:
                detail.append("desconhecidas: " + ", ".join(unknown))
            raise BackupValidationError("O backup não corresponde à estrutura atual do sistema (" + "; ".join(detail) + ").")
        if not supplied:
            raise BackupValidationError("O backup não contém tabelas do banco de dados.")

        identifiers = ", ".join(_quote_identifier(name) for name in sorted(supplied))
        cursor.execute(f"TRUNCATE TABLE {identifiers} RESTART IDENTITY CASCADE")
        restored = 0
        pending = set(supplied)
        # Tenta repetidamente: chaves estrangeiras determinam naturalmente a ordem.
        while pending:
            progress = False
            last_error = None
            for name in sorted(pending):
                rows = tables[name]["rows"]
                savepoint = "restore_" + hashlib.sha1(name.encode()).hexdigest()[:12]
                cursor.execute(f"SAVEPOINT {savepoint}")
                try:
                    if rows:
                        identifier = _quote_identifier(name)
                        payload = json.dumps(rows, ensure_ascii=False, default=_json_default)
                        cursor.execute(
                            f"INSERT INTO {identifier} OVERRIDING SYSTEM VALUE "
                            f"SELECT * FROM json_populate_recordset(NULL::{identifier}, %s::json)",
                            (payload,),
                        )
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint}")
                except Exception as exc:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint}")
                    last_error = exc
                    continue
                restored += len(rows)
                pending.remove(name)
                progress = True
            if not progress:
                raise BackupValidationError("Não foi possível recompor os relacionamentos entre as tabelas.") from last_error
        connection.commit()
        return restored
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _restore_local(data_root: Path, files: dict[str, bytes]) -> int:
    data_root.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for relative, content in files.items():
            target = data_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary = tempfile.mkstemp(prefix=".restore-", dir=target.parent)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            staged.append((Path(temporary), target))
        for temporary, target in staged:
            os.replace(temporary, target)
        return len(files)
    finally:
        for temporary, _target in staged:
            temporary.unlink(missing_ok=True)


def restore_complete_backup(legacy, upload: bytes) -> dict[str, Any]:
    """Restaura um backup validado; PostgreSQL usa uma única transação."""
    manifest, tables, files = inspect_complete_backup(upload)
    if getattr(legacy, "USE_POSTGRES", False):
        restored_rows = _restore_postgres(legacy, tables)
    else:
        restored_rows = 0
    restored_files = _restore_local(Path(legacy.DATA), files)
    return {
        "generated_at": manifest.get("generated_at"),
        "tables": len(tables),
        "rows": restored_rows,
        "files": restored_files,
    }
