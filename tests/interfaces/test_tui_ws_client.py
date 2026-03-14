"""Tests for the server-backed TUI WebSocket client."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from doorae.interfaces.tui import (
    AgendaUpdated,
    HumanTurnStarted,
    MeetingEnded,
    ParticipantStatusChanged,
    SpeakerChanged,
    StreamError,
    TokenStreamed,
    ToolCallEnded,
    ToolCallStarted,
    TurnCompleted,
)
from doorae.interfaces.tui_ws_client import ServerEventClient


class RecordingApp:
    def __init__(self) -> None:
        self.messages: list[object] = []

    def post_message(self, message: object) -> None:
        self.messages.append(message)


class MockConnection:
    def __init__(self, websocket: AsyncMock | None = None, enter_error: Exception | None = None) -> None:
        self._websocket = websocket
        self._enter_error = enter_error

    async def __aenter__(self) -> AsyncMock:
        if self._enter_error is not None:
            raise self._enter_error
        if self._websocket is None:
            raise AssertionError("websocket is required")
        return self._websocket

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _patch_connect(monkeypatch: pytest.MonkeyPatch, connection: MockConnection) -> list[str]:
    urls: list[str] = []

    def fake_connect(ws_url: str) -> MockConnection:
        urls.append(ws_url)
        return connection

    monkeypatch.setattr("doorae.interfaces.tui_ws_client.connect", fake_connect)
    return urls


@pytest.mark.asyncio
async def test_run_dispatches_semantic_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    app = RecordingApp()
    websocket = AsyncMock()
    websocket.recv = AsyncMock(
        side_effect=[
            json.dumps(
                {
                    "type": "semantic:pending_speakers_changed",
                    "data": {"pending_speakers": ["Bob", "Carol"]},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:speaker_changed",
                    "data": {"speaker": "Alice", "is_delegated": False},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:token",
                    "data": {
                        "content": "안녕하세요",
                        "speaker": "Alice",
                        "is_delegated": True,
                    },
                }
            ),
            json.dumps(
                {
                    "type": "semantic:turn_completed",
                    "data": {"speaker": "Alice", "is_delegated": True},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:human_turn_started",
                    "data": {"username": "Dana"},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:agenda_updated",
                    "data": {
                        "agendas": [{"title": "예산", "status": "in_progress"}],
                        "current_idx": 0,
                    },
                }
            ),
            json.dumps(
                {
                    "type": "semantic:meeting_ended",
                    "data": {
                        "agendas": [{"title": "예산", "status": "completed"}],
                        "speaker_counts": {"Alice": 2},
                    },
                }
            ),
            json.dumps(
                {
                    "type": "semantic:participant_status_changed",
                    "data": {"participant_name": "Alice", "status": "speaking"},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:tool_call",
                    "data": {"name": "web_search", "status": "started"},
                }
            ),
            json.dumps(
                {
                    "type": "semantic:tool_call",
                    "data": {"name": "web_search", "status": "ended"},
                }
            ),
            StopAsyncIteration(),
        ]
    )
    urls = _patch_connect(monkeypatch, MockConnection(websocket=websocket))

    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    await client.run()

    assert urls == ["ws://example/ws/room?username=alice"]
    assert [type(message) for message in app.messages] == [
        SpeakerChanged,
        TokenStreamed,
        TurnCompleted,
        HumanTurnStarted,
        AgendaUpdated,
        MeetingEnded,
        ParticipantStatusChanged,
        ToolCallStarted,
        ToolCallEnded,
        StreamError,
    ]

    speaker_changed = app.messages[0]
    assert isinstance(speaker_changed, SpeakerChanged)
    assert speaker_changed.pending == ["Bob", "Carol"]

    token = app.messages[1]
    assert isinstance(token, TokenStreamed)
    assert token.token == "안녕하세요"
    assert token.agent_name == "Alice"
    assert token.is_delegated is True

    turn = app.messages[2]
    assert isinstance(turn, TurnCompleted)
    assert turn.is_delegated is True

    human_turn = app.messages[3]
    assert isinstance(human_turn, HumanTurnStarted)
    assert human_turn.username == "Dana"

    agenda = app.messages[4]
    assert isinstance(agenda, AgendaUpdated)
    assert agenda.current_idx == 0

    meeting_end = app.messages[5]
    assert isinstance(meeting_end, MeetingEnded)
    assert meeting_end.speaker_counts == {"Alice": 2}

    participant = app.messages[6]
    assert isinstance(participant, ParticipantStatusChanged)
    assert participant.participant_name == "Alice"
    assert participant.status == "speaking"

    tool_start = app.messages[7]
    tool_end = app.messages[8]
    assert isinstance(tool_start, ToolCallStarted)
    assert isinstance(tool_end, ToolCallEnded)

    disconnect = app.messages[9]
    assert isinstance(disconnect, StreamError)
    assert "종료" in disconnect.error


@pytest.mark.asyncio
async def test_run_emits_stream_error_on_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = RecordingApp()
    _patch_connect(monkeypatch, MockConnection(enter_error=OSError("Connection refused")))

    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    await client.run()

    assert len(app.messages) == 1
    error = app.messages[0]
    assert isinstance(error, StreamError)
    assert "Connection refused" in error.error


@pytest.mark.asyncio
async def test_run_ignores_malformed_and_unknown_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = RecordingApp()
    websocket = AsyncMock()
    websocket.recv = AsyncMock(
        side_effect=[
            "not-json",
            json.dumps({"type": "system", "data": {"message": "joined"}}),
            json.dumps({"type": "semantic:unknown", "data": {"value": 1}}),
            json.dumps({"type": "semantic:token", "data": {"speaker": "Alice"}}),
            StopAsyncIteration(),
        ]
    )
    _patch_connect(monkeypatch, MockConnection(websocket=websocket))

    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    await client.run()

    assert len(app.messages) == 1
    error = app.messages[0]
    assert isinstance(error, StreamError)
    assert "종료" in error.error


@pytest.mark.asyncio
async def test_run_emits_stream_error_for_server_error_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = RecordingApp()
    websocket = AsyncMock()
    websocket.recv = AsyncMock(
        side_effect=[
            json.dumps({"type": "error", "data": {"error": "boom"}}),
            StopAsyncIteration(),
        ]
    )
    _patch_connect(monkeypatch, MockConnection(websocket=websocket))

    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    await client.run()

    assert len(app.messages) == 2
    first = app.messages[0]
    assert isinstance(first, StreamError)
    assert first.error == "boom"


@pytest.mark.asyncio
async def test_send_input_serializes_content() -> None:
    app = RecordingApp()
    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    websocket = AsyncMock()
    client._websocket = websocket

    await client.send_input("찬성합니다")

    websocket.send.assert_awaited_once_with(json.dumps({"content": "찬성합니다"}))


@pytest.mark.asyncio
async def test_send_input_without_connection_emits_error() -> None:
    app = RecordingApp()
    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)

    await client.send_input("찬성합니다")

    assert len(app.messages) == 1
    error = app.messages[0]
    assert isinstance(error, StreamError)
    assert "연결" in error.error


@pytest.mark.asyncio
async def test_wait_until_connected_tracks_connection_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = RecordingApp()
    release = asyncio.Event()
    websocket = AsyncMock()

    async def recv_side_effect() -> str:
        await release.wait()
        raise StopAsyncIteration()

    websocket.recv = AsyncMock(side_effect=recv_side_effect)
    _patch_connect(monkeypatch, MockConnection(websocket=websocket))

    client = ServerEventClient("ws://example/ws/room?username=alice", "alice", app)
    run_task = asyncio.create_task(client.run())

    await client.wait_until_connected()
    assert client.connected.is_set() is True

    release.set()
    await run_task

    assert client.connected.is_set() is False
