"""Tests for CLI agenda panel rendering."""

from unittest.mock import patch

from doorae.interfaces.cli import format_agenda_panel


def test_format_agenda_panel_uses_shared_time_format() -> None:
    agendas = [
        {
            "title": "진행중 안건",
            "status": "in_progress",
            "required_speakers": ["alice"],
            "start_time": 100.0,
        },
        {
            "title": "완료 안건",
            "status": "completed",
            "required_speakers": ["bob"],
            "start_time": 20.0,
            "end_time": 95.0,
        },
    ]

    with patch("doorae.interfaces.cli.time.time", return_value=165.0):
        panel = format_agenda_panel(agendas=agendas, current_idx=0, start_time=100.0)

    text = str(panel.renderable)
    assert "진행중 안건 (alice) [01:05] ← 현재" in text
    assert "완료 안건 (bob) [01:15]" in text
    assert "1m 5s" not in text
