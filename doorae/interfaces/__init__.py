"""User interfaces for Doorae."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["MeetingTuiApp"]

if TYPE_CHECKING:
    from doorae.interfaces.tui import MeetingTuiApp


def __getattr__(name: str):
    if name != "MeetingTuiApp":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from doorae.interfaces.tui import MeetingTuiApp

    return MeetingTuiApp
