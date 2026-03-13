"""Date context helpers for agent prompts."""

from __future__ import annotations

from datetime import datetime


_WEEKDAYS = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}


def format_today_context(now: datetime | None = None) -> str:
    """Return today's date in a Korean natural-language format."""
    current = now or datetime.now()
    weekday = _WEEKDAYS[current.weekday()]
    return f"오늘은 {current.year}년 {current.month}월 {current.day}일 ({weekday})입니다."
