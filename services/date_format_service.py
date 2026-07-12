"""Brazilian display formatting without changing stored ISO dates."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def _parse(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
    return None


def format_date_br(value: Any, fallback: str = "—") -> str:
    parsed = _parse(value)
    return parsed.strftime("%d/%m/%Y") if parsed else (str(value) if value else fallback)


def format_datetime_br(value: Any, fallback: str = "—") -> str:
    parsed = _parse(value)
    return parsed.strftime("%d/%m/%Y às %H:%M") if parsed else (str(value) if value else fallback)


def format_month_br(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    if len(text) >= 7 and text[4] in "-/" and text[:4].isdigit() and text[5:7].isdigit():
        return f"{text[5:7]}/{text[:4]}"
    return text or fallback
