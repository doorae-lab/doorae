"""Time formatting helpers for interfaces."""

from __future__ import annotations


def format_elapsed(seconds: int) -> str:
    """Format elapsed seconds as MM:SS (under 1 hour) or HH:MM:SS."""
    safe_seconds = max(0, seconds)
    hours, remainder = divmod(safe_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
