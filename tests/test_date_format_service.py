from datetime import date, datetime

from services.date_format_service import format_date_br, format_datetime_br, format_month_br


def test_formats_iso_dates_for_brazilian_display():
    assert format_date_br("2026-07-12") == "12/07/2026"
    assert format_date_br(date(2026, 8, 21)) == "21/08/2026"
    assert format_datetime_br("2026-07-12T14:35:00") == "12/07/2026 às 14:35"
    assert format_datetime_br(datetime(2026, 7, 12, 9, 5)) == "12/07/2026 às 09:05"


def test_formats_month_and_preserves_empty_fallback():
    assert format_month_br("2026-07") == "07/2026"
    assert format_date_br("") == "—"
    assert format_date_br("", "Data não registrada") == "Data não registrada"
