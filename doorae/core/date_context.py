"""Date context helpers for agent prompts."""

from __future__ import annotations

from datetime import datetime


_WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def format_today_context(now: datetime | None = None) -> str:
    """Return today's date in an English prompt-friendly format."""
    current = now or datetime.now()
    weekday = _WEEKDAYS[current.weekday()]
    return f"Today is {current.year:04d}-{current.month:02d}-{current.day:02d} ({weekday})."
