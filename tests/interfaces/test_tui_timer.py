"""Focused tests for TUI timer behavior."""

from __future__ import annotations

from unittest.mock import patch

from thetable.interfaces.tui import AgendaPanel, MeetingEnded, MeetingTuiApp


class CapturingAgendaPanel(AgendaPanel):
    def __init__(self) -> None:
        super().__init__()
        self.last_rendered = ""

    def update(self, renderable: object = "", *args: object, **kwargs: object) -> None:
        self.last_rendered = str(renderable)


class DummyTimer:
    def __init__(self) -> None:
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def _build_app() -> MeetingTuiApp:
    return MeetingTuiApp(settings=object(), profiles_path="profiles.yaml", initial_message="start")


def test_agenda_panel_renders_total_and_agenda_elapsed_time() -> None:
    panel = CapturingAgendaPanel()
    panel.update_timer("00:42")
    panel.update_meeting_start_time(100.0)
    agendas = [
        {"title": "A", "status": "in_progress", "start_time": 120.0},
        {"title": "B", "status": "completed", "start_time": 60.0, "end_time": 90.0},
    ]

    with patch("thetable.interfaces.tui.time.time", return_value=180.0):
        panel.update_agendas(agendas, 0)

    assert "⏱ 총 경과: 00:42" in panel.last_rendered
    assert "A [01:00] ◀" in panel.last_rendered
    assert "B [00:30]" in panel.last_rendered


def test_tick_timer_updates_panel_with_formatted_elapsed() -> None:
    app = _build_app()
    app._meeting_start_time = 100.0
    panel = CapturingAgendaPanel()
    app.query_one = lambda *_args, **_kwargs: panel  # type: ignore[method-assign]

    with patch("thetable.interfaces.tui.time.time", return_value=165.0):
        app._tick_timer()

    assert "⏱ 총 경과: 01:05" in panel.last_rendered


def test_meeting_ended_stops_interval_timer() -> None:
    app = _build_app()
    timer = DummyTimer()
    app._timer_interval = timer  # type: ignore[assignment]
    app._tick_timer = lambda: None  # type: ignore[method-assign]
    app._render_summary = lambda: None  # type: ignore[method-assign]

    app.on_meeting_ended(MeetingEnded(agendas=[], speaker_counts={}))

    assert timer.stopped is True
    assert app._timer_interval is None
    assert app.meeting_status == "ended"


def test_render_summary_includes_total_and_agenda_durations() -> None:
    app = _build_app()
    app._meeting_start_time = 100.0
    app._last_agendas = [
        {"title": "A", "status": "completed", "decision": "done", "start_time": 110.0, "end_time": 150.0},
        {"title": "B", "status": "in_progress", "decision": "-", "start_time": 130.0},
    ]
    app._update_conversation = lambda: None  # type: ignore[method-assign]

    with patch("thetable.interfaces.tui.time.time", return_value=190.0):
        app._render_summary()

    assert "⏱ 총 경과: 01:30" in app._full_text
    assert "A" in app._full_text and "소요: 00:40" in app._full_text
    assert "B" in app._full_text and "소요: 01:00" in app._full_text
