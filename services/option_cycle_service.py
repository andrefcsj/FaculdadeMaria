"""Classificação centralizada de opções mensais e semanais."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any


WEEKLY_SUFFIX = re.compile(r"W([1-5])$", re.IGNORECASE)


def classify_option_cycle(option_code: Any) -> dict[str, Any]:
    """Identifica séries semanais pelo sufixo usado no cadastro (W1...W5)."""
    code = str(option_code or "").strip().upper()
    match = WEEKLY_SUFFIX.search(code)
    week = int(match.group(1)) if match else None
    return {
        "is_weekly": week is not None,
        "cycle": "weekly" if week is not None else "monthly",
        "week_number": week,
        "cycle_label": f"Semanal · {week}ª semana" if week is not None else "Mensal",
    }


def _decimal(value: Any) -> Decimal:
    text = str(value or "0").strip().replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text or "0")
    except InvalidOperation:
        return Decimal("0")


def build_cycle_groups(
    operations: list[dict[str, Any]], *, result_key: str, capital_key: str
) -> list[dict[str, Any]]:
    """Separa mensais e semanais e calcula o ROI ponderado de cada bloco."""
    groups = []
    definitions = (
        ("monthly", "Opções mensais", "Séries tradicionais, sem sufixo semanal"),
        ("weekly", "Opções semanais", "Séries W1 a W5, agrupadas por vencimento semanal"),
    )
    for cycle, label, description in definitions:
        rows = [operation for operation in operations if operation.get("cycle") == cycle]
        result = sum((_decimal(operation.get(result_key)) for operation in rows), Decimal("0"))
        capital = sum((_decimal(operation.get(capital_key)) for operation in rows), Decimal("0"))
        groups.append({
            "cycle": cycle,
            "label": label,
            "description": description,
            "operations": rows,
            "count": len(rows),
            "result": result,
            "capital": capital,
            "roi": result / capital * Decimal("100") if capital else Decimal("0"),
        })
    return groups
