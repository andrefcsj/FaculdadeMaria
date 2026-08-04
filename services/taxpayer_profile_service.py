"""Dados mínimos do contribuinte usados exclusivamente na emissão do DARF."""
from __future__ import annotations
import json
from pathlib import Path

FIELDS = ("name", "cpf", "phone", "city", "state")

def _path(legacy) -> Path:
    return legacy.DATA / "taxpayer_profile.json"

def load_taxpayer_profile(legacy):
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor(); cur.execute("CREATE TABLE IF NOT EXISTS taxpayer_profile (profile_id INTEGER PRIMARY KEY, payload JSONB NOT NULL)"); conn.commit()
            cur.execute("SELECT payload FROM taxpayer_profile WHERE profile_id=1"); row = cur.fetchone()
            return row[0] if row and isinstance(row[0], dict) else (json.loads(row[0]) if row else {})
        finally: conn.close()
    path = _path(legacy)
    try: return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception: return {}

def save_taxpayer_profile(legacy, payload):
    profile = {field: str(payload.get(field, "")).strip() for field in FIELDS}
    digits = "".join(ch for ch in profile["cpf"] if ch.isdigit())
    if not profile["name"] or len(digits) != 11 or not profile["city"] or len(profile["state"]) != 2:
        raise ValueError("Informe nome, CPF válido, município e UF para gerar a guia.")
    profile["cpf"] = digits; profile["state"] = profile["state"].upper()
    if getattr(legacy, "USE_POSTGRES", False):
        conn = legacy.get_pg_conn()
        try:
            cur = conn.cursor(); cur.execute("CREATE TABLE IF NOT EXISTS taxpayer_profile (profile_id INTEGER PRIMARY KEY, payload JSONB NOT NULL)")
            cur.execute("INSERT INTO taxpayer_profile(profile_id,payload) VALUES(1,%s::jsonb) ON CONFLICT(profile_id) DO UPDATE SET payload=EXCLUDED.payload", (json.dumps(profile, ensure_ascii=False),)); conn.commit()
        finally: conn.close()
    else:
        path = _path(legacy); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile
