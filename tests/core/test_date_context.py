from datetime import datetime

from doorae.core.date_context import format_today_context


def test_format_today_context_returns_english_date_context():
    assert (
        format_today_context(datetime(2026, 3, 13))
        == "Today is 2026-03-13 (Friday)."
    )
