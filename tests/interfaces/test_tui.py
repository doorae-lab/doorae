"""TUI human input panel tests."""

from __future__ import annotations

import pytest
from textual.widgets import Markdown, Static

from doorae.config import Settings
from doorae.interfaces.tui import (
    HumanTurnStarted,
    MeetingTuiApp,
    ParticipantPanel,
    ServerConnected,
    SpeakerChanged,
    SpeechBubble,
    SpinnerWidget,
    SubmittableTextArea,
)


class DummyMeetingTuiApp(MeetingTuiApp):
    """Disable workflow startup for deterministic UI tests."""

    async def on_mount(self) -> None:
        return

    def run_meeting_worker(self) -> None:
        return


class RecordingInputProvider:
    def __init__(self) -> None:
        self.submitted: list[str] = []

    def submit_input(self, value: str) -> None:
        self.submitted.append(value)


class RecordingServerClient:
    def __init__(self) -> None:
        self.submitted: list[str] = []
        self.closed = False

    async def send_input(self, value: str) -> None:
        self.submitted.append(value)

    async def close(self) -> None:
        self.closed = True


class InspectServerBackedTuiApp(MeetingTuiApp):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.server_worker_called = False

    def run_server_worker(self) -> None:
        self.server_worker_called = True


def _static_text(widget: Static) -> str:
    return str(widget.content)


def _speaker_bubbles(app: MeetingTuiApp, speaker: str) -> list[SpeechBubble]:
    return [bubble for bubble in app.query(SpeechBubble) if bubble._speaker == speaker]


def _conversation_texts(app: MeetingTuiApp) -> list[str]:
    scroll = app.query_one("#conversation-scroll")
    return [_static_text(widget) for widget in scroll.query(Static)]


def _submitted_event(
    text_area: SubmittableTextArea, value: str
) -> SubmittableTextArea.Submitted:
    return SubmittableTextArea.Submitted(text_area=text_area, value=value)


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
        assert "Ctrl+J" in _static_text(label)


@pytest.mark.asyncio
async def test_watch_input_enabled_toggles_panel_and_focus() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )
    async with app.run_test() as pilot:
        panel = app.query_one("#human-input-panel")
        input_widget = app.query_one("#input-area", SubmittableTextArea)

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


@pytest.mark.asyncio
async def test_input_submission_mounts_human_bubble_and_forwards_value() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        input_provider = RecordingInputProvider()
        app._input_provider = input_provider
        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        await pilot.pause()

        input_widget = app.query_one("#input-area", SubmittableTextArea)
        app.on_submittable_text_area_submitted(_submitted_event(input_widget, "찬성합니다"))
        await pilot.pause()

        bubbles = _speaker_bubbles(app, "민지")
        panel = app.query_one("#human-input-panel")

        assert input_provider.submitted == ["찬성합니다"]
        assert len(bubbles) == 1
        assert bubbles[0]._buffer == "찬성합니다"
        assert "human" in bubbles[0].classes
        assert bubbles[0]._body is None
        assert bubbles[0].query_one(Markdown)
        assert "visible" not in panel.classes
        assert app._current_human_speaker == ""


@pytest.mark.asyncio
async def test_ai_bubble_does_not_have_human_class() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        app.on_speaker_changed(SpeakerChanged(speaker="ai-agent", pending=[]))
        await pilot.pause()

        bubbles = _speaker_bubbles(app, "ai-agent")

        assert len(bubbles) == 1
        assert "human" not in bubbles[0].classes


@pytest.mark.asyncio
async def test_server_mode_mount_uses_websocket_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubServerEventClient:
        def __init__(self, ws_url: str, username: str, app: MeetingTuiApp) -> None:
            self.ws_url = ws_url
            self.username = username
            self.app = app

        async def close(self) -> None:
            return

    monkeypatch.setattr("doorae.interfaces.tui_ws_client.ServerEventClient", StubServerEventClient)

    app = InspectServerBackedTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_start_url="http://localhost:8000/api/rooms/room-123/start",
        server_username="alice",
    )

    async with app.run_test():
        assert app._engine is None
        assert app._input_provider is None
        assert isinstance(app._ws_client, StubServerEventClient)
        assert app._ws_client.ws_url == "ws://localhost:8000/ws/room-123?username=alice"
        assert app.server_worker_called is True


@pytest.mark.asyncio
async def test_server_mode_mount_shows_room_and_initial_participant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubServerEventClient:
        def __init__(self, ws_url: str, username: str, app: MeetingTuiApp) -> None:
            self.ws_url = ws_url
            self.username = username
            self.app = app

        async def close(self) -> None:
            return

    monkeypatch.setattr("doorae.interfaces.tui_ws_client.ServerEventClient", StubServerEventClient)

    app = InspectServerBackedTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_start_url="http://localhost:8000/api/rooms/room-123/start",
        server_username="alice",
        room_id="room-123",
    )

    async with app.run_test():
        participant_panel = app.query_one("#participant-panel", ParticipantPanel)
        assert app.sub_title == "Room: room-123"
        assert participant_panel._statuses["alice"] == "idle"
        assert "alice" in participant_panel._participant_nodes

        app.on_speaker_changed(SpeakerChanged(speaker="host-agent", pending=[]))
        assert app.sub_title == "Room: room-123 | 발언자: host-agent"


@pytest.mark.asyncio
async def test_server_mode_mount_shows_connecting_spinner_and_invite_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubServerEventClient:
        def __init__(self, ws_url: str, username: str, app: MeetingTuiApp) -> None:
            self.ws_url = ws_url
            self.username = username
            self.app = app

        async def close(self) -> None:
            return

    monkeypatch.setattr("doorae.interfaces.tui_ws_client.ServerEventClient", StubServerEventClient)

    app = InspectServerBackedTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_start_url="http://localhost:8000/api/rooms/room-123/start",
        server_username="alice",
        room_id="room-123",
        show_server_invite=True,
    )

    async with app.run_test():
        spinners = [spinner for spinner in app.query(SpinnerWidget)]
        assert len(spinners) == 1
        assert spinners[0]._label == "서버에 연결 중..."
        assert any(
            "doorae join room-123 -s localhost:8000 -u <name>" in text
            for text in _conversation_texts(app)
        )


@pytest.mark.asyncio
async def test_server_connected_removes_spinner_and_shows_connected_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubServerEventClient:
        def __init__(self, ws_url: str, username: str, app: MeetingTuiApp) -> None:
            self.ws_url = ws_url
            self.username = username
            self.app = app

        async def close(self) -> None:
            return

    monkeypatch.setattr("doorae.interfaces.tui_ws_client.ServerEventClient", StubServerEventClient)

    app = InspectServerBackedTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_start_url="http://localhost:8000/api/rooms/room-123/start",
        server_username="alice",
        room_id="room-123",
    )

    async with app.run_test() as pilot:
        assert len([spinner for spinner in app.query(SpinnerWidget)]) == 1

        app.on_server_connected(ServerConnected())
        await pilot.pause()

        assert [spinner for spinner in app.query(SpinnerWidget)] == []
        assert any("서버에 연결되었습니다." in text for text in _conversation_texts(app))


@pytest.mark.asyncio
async def test_server_mode_input_submission_sends_over_websocket() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_start_url="http://localhost:8000/api/rooms/room-123/start",
        server_username="alice",
    )

    async with app.run_test() as pilot:
        ws_client = RecordingServerClient()
        app._ws_client = ws_client
        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        await pilot.pause()

        input_widget = app.query_one("#input-area", SubmittableTextArea)
        app.on_submittable_text_area_submitted(_submitted_event(input_widget, "찬성합니다"))
        await pilot.pause()

        bubbles = _speaker_bubbles(app, "민지")
        panel = app.query_one("#human-input-panel")

        assert ws_client.submitted == ["찬성합니다"]
        assert len(bubbles) == 1
        assert bubbles[0]._buffer == "찬성합니다"
        assert "visible" not in panel.classes
        assert app._current_human_speaker == ""


@pytest.mark.asyncio
async def test_blank_input_submission_skips_human_bubble() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        input_provider = RecordingInputProvider()
        app._input_provider = input_provider
        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        await pilot.pause()

        input_widget = app.query_one("#input-area", SubmittableTextArea)
        app.on_submittable_text_area_submitted(_submitted_event(input_widget, "   "))
        await pilot.pause()

        assert input_provider.submitted == ["   "]
        assert _speaker_bubbles(app, "민지") == []
        assert app._current_human_speaker == ""


@pytest.mark.asyncio
async def test_multiline_input_submission() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        input_provider = RecordingInputProvider()
        app._input_provider = input_provider
        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        await pilot.pause()

        input_widget = app.query_one("#input-area", SubmittableTextArea)
        input_widget.insert("첫줄")
        await pilot.press("ctrl+j")
        await pilot.pause()
        assert input_widget.text == "첫줄\n"

        input_widget.insert("둘째줄")
        await pilot.press("enter")
        await pilot.pause()

        assert input_provider.submitted == ["첫줄\n둘째줄"]
        assert input_widget.text == ""
        assert _speaker_bubbles(app, "민지")[0]._buffer == "첫줄\n둘째줄"


@pytest.mark.asyncio
async def test_ctrl_d_toggle_delegated_while_text_area_focused() -> None:
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        app.on_human_turn_started(HumanTurnStarted(username="민지"))
        await pilot.pause()

        input_widget = app.query_one("#input-area", SubmittableTextArea)
        assert input_widget.has_focus
        assert app.show_delegated is True

        await pilot.press("ctrl+d")
        await pilot.pause()

        assert app.show_delegated is False
        assert input_widget.text == ""


# ── 서버 모드: 다른 사용자 차례일 때 입력 비활성화 테스트 ──


@pytest.mark.asyncio
async def test_server_mode_other_user_turn_does_not_enable_input() -> None:
    """서버 모드에서 다른 사용자 차례일 때 input_enabled는 False."""
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_username="alice",
    )

    async with app.run_test() as pilot:
        app._last_agendas = [{"title": "안건1", "status": "pending"}]
        app.current_agenda_idx = 0

        # 다른 사용자(Bob)의 차례 이벤트
        app.on_human_turn_started(HumanTurnStarted(username="Bob"))
        await pilot.pause()

        panel = app.query_one("#human-input-panel")
        label = app.query_one("#human-input-label", Static)

        # 입력 패널이 활성화되지 않아야 함
        assert app.input_enabled is False
        assert "visible" not in panel.classes
        # "입력 중" 표시
        label_text = _static_text(label)
        assert "Bob" in label_text
        assert "입력 중" in label_text


@pytest.mark.asyncio
async def test_server_mode_own_turn_enables_input() -> None:
    """서버 모드에서 자신의 차례일 때 input_enabled는 True."""
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
        server_url="ws://localhost:8000/ws/room-123?username=alice",
        server_username="alice",
    )

    async with app.run_test() as pilot:
        app._last_agendas = [{"title": "안건1", "status": "pending"}]
        app.current_agenda_idx = 0

        # 자신(alice)의 차례 이벤트
        app.on_human_turn_started(HumanTurnStarted(username="alice"))
        await pilot.pause()

        panel = app.query_one("#human-input-panel")
        label = app.query_one("#human-input-label", Static)

        # 입력 패널이 활성화되어야 함
        assert app.input_enabled is True
        assert "visible" in panel.classes
        label_text = _static_text(label)
        assert "alice의 차례" in label_text


@pytest.mark.asyncio
async def test_local_mode_always_enables_input() -> None:
    """로컬 모드에서는 항상 입력이 활성화됨."""
    app = DummyMeetingTuiApp(
        settings=Settings(),
        profiles_path="config/agent_profiles.yaml",
        initial_message="hello",
    )

    async with app.run_test() as pilot:
        app._last_agendas = [{"title": "안건1", "status": "pending"}]
        app.current_agenda_idx = 0

        app.on_human_turn_started(HumanTurnStarted(username="Bob"))
        await pilot.pause()

        # 로컬 모드에서는 항상 활성화
        assert app.input_enabled is True
        panel = app.query_one("#human-input-panel")
        assert "visible" in panel.classes
