from datetime import datetime

from doorae.core.date_context import format_today_context


def test_format_today_context_returns_korean_natural_language_date():
    assert (
        format_today_context(datetime(2026, 3, 13))
        == "오늘은 2026년 3월 13일 (금요일)입니다."
    )
