"""Cadastro pessoal de ativos analisáveis para eventual exercício de PUT."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from engine import AssetQualityProfile


REQUIRED_COLUMNS = (
    "option_root", "ticker", "assignment_eligible", "long_term_suitable",
    "quality_score", "data_confidence", "notes",
)


def _boolean(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "sim", "yes"}


def _score(value: str) -> Decimal | None:
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Nota inválida: {value}") from exc
    if not Decimal("0") <= result <= Decimal("1"):
        raise ValueError("Notas devem estar entre 0 e 1")
    return result


def load_personal_asset_universe(path: str | Path) -> tuple[dict[str, str], dict[str, AssetQualityProfile]]:
    """Return option-root mapping and Decision Engine quality profiles.

    The file starts empty by design: no asset is approved implicitly.
    """
    source = Path(path)
    if not source.exists():
        return {}, {}
    roots: dict[str, str] = {}
    profiles: dict[str, AssetQualityProfile] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or any(column not in reader.fieldnames for column in REQUIRED_COLUMNS):
            raise ValueError("Cadastro de ativos possui colunas ausentes")
        for row in reader:
            ticker = str(row.get("ticker", "")).strip().upper()
            root = str(row.get("option_root", "")).strip().upper()
            if not ticker or not root:
                continue
            eligible = _boolean(row.get("assignment_eligible", ""))
            suitable = _boolean(row.get("long_term_suitable", ""))
            quality = _score(row.get("quality_score", ""))
            confidence = _score(row.get("data_confidence", ""))
            notes = str(row.get("notes", "")).strip()
            roots[root] = ticker
            profiles[ticker] = AssetQualityProfile(
                asset=ticker,
                assignment_eligible=eligible,
                long_term_suitable=suitable,
                quality_score=quality,
                data_confidence=confidence,
                warnings=(() if eligible and suitable else ("Ativo não aprovado para eventual exercício",)),
                positive_notes=((notes,) if notes and eligible and suitable else ()),
                blocking_events=(() if eligible and suitable else ("Aprovação pessoal pendente ou recusada",)),
                source="universo_pessoal",
            )
    return roots, profiles
