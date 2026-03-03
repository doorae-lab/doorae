"""TUI human input panel tests."""

from __future__ import annotations

import pytest
from textual.widgets import Input, Static

from thetable.config import Settings
from thetable.interfaces.tui import HumanTurnStarted, MeetingTuiApp, SpeakerChanged


class DummyMeetingTuiApp(MeetingTuiApp):
    """Disable workflow startup for deterministic UI tests."""

    async def on_mount(self) -> None:
        return


def _static_text(widget: Static) -> str:
    return str(widget.content)


@pytest.mark.asyncio
async def test_human_input_panel_hidden_by_default() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )
    async with app.run_test():
        panel = app.query_one("#human-input-panel")
        label = app.query_one("#human-input-label", Static)
        assert "visible" not in panel.classes
        assert "의견을 입력하세요" in _static_text(label)


@pytest.mark.asyncio
async def test_watch_input_enabled_toggles_panel_and_focus() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )
    async with app.run_test() as pilot:
        panel = app.query_one("#human-input-panel")
        input_widget = app.query_one("#input-area", Input)

        app.watch_input_enabled(True)
        await pilot.pause()
        assert "visible" in panel.classes
        assert input_widget.has_focus

        app.watch_input_enabled(False)
        await pilot.pause()
        assert "visible" not in panel.classes


@pytest.mark.asyncio
async def test_human_turn_label_includes_username_and_agenda_title() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )
    async with app.run_test():
        app._last_agendas = [{"title": "예산 승인", "status": "pending"}]
        app.current_agenda_idx = 0

        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        label = app.query_one("#human-input-label", Static)
        panel = app.query_one("#human-input-panel")

        assert "[민지의 차례] 예산 승인" in _static_text(label)
        assert "visible" in panel.classes

        app.on_speaker_changed(SpeakerChanged(speaker="ai-agent", pending=[]))
        assert "visible" not in panel.classes


@pytest.mark.asyncio
async def test_get_current_agenda_title_fallbacks() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )
    async with app.run_test():
        app._last_agendas = []
        app.current_agenda_idx = 0
        assert app._get_current_agenda_title() == "안건 미지정"

        app._last_agendas = [{"title": "로드맵"}]
        app.current_agenda_idx = 2
        assert app._get_current_agenda_title() == "안건 미지정"

        app.current_agenda_idx = 0
        assert app._get_current_agenda_title() == "로드맵"
