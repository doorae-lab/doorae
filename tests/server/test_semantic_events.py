"""Server semantic event broadcasting tests."""

from __future__ import annotations

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from doorae.server.events import format_semantic_event
from doorae.server.room import ServerMeetingCallback


def _assert_timestamp_isoformat(value: str) -> None:
    assert value
    datetime.fromisoformat(value)


def _connection_manager() -> SimpleNamespace:
    return SimpleNamespace(broadcast=AsyncMock())


def test_format_semantic_event_adds_namespace_and_timestamp() -> None:
    event = format_semantic_event(
        "token",
        content="안녕",
        speaker="Alice",
        is_delegated=False,
    )

    assert event["type"] == "semantic:token"
    assert event["data"] == {
        "content": "안녕",
        "speaker": "Alice",
        "is_delegated": False,
    }
    _assert_timestamp_isoformat(event["timestamp"])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "kwargs", "expected_type", "expected_data"),
    [
        (
            "on_speaker_changed",
            {"speaker": "Alice", "is_delegated": True},
            "semantic:speaker_changed",
            {"speaker": "Alice", "is_delegated": True},
        ),
        (
            "on_token",
            {"content": "토큰", "speaker": "Alice", "is_delegated": False},
            "semantic:token",
            {"content": "토큰", "speaker": "Alice", "is_delegated": False},
        ),
        (
            "on_turn_completed",
            {"speaker": "Alice", "is_delegated": False},
            "semantic:turn_completed",
            {"speaker": "Alice", "is_delegated": False},
        ),
        (
            "on_human_turn_started",
            {"username": "Bob"},
            "semantic:human_turn_started",
            {"username": "Bob"},
        ),
        (
            "on_agenda_updated",
            {
                "agendas": [{"title": "예산 승인", "status": "in_progress"}],
                "current_idx": 1,
            },
            "semantic:agenda_updated",
            {
                "agendas": [{"title": "예산 승인", "status": "in_progress"}],
                "current_idx": 1,
            },
        ),
        (
            "on_meeting_ended",
            {
                "agendas": [{"title": "예산 승인", "status": "completed"}],
                "speaker_counts": {"Alice": 3},
            },
            "semantic:meeting_ended",
            {
                "agendas": [{"title": "예산 승인", "status": "completed"}],
                "speaker_counts": {"Alice": 3},
            },
        ),
        (
            "on_pending_speakers_changed",
            {"pending_speakers": ["Carol", "Dave"]},
            "semantic:pending_speakers_changed",
            {"pending_speakers": ["Carol", "Dave"]},
        ),
        (
            "on_participant_status_changed",
            {"participant_name": "Alice", "status": "speaking"},
            "semantic:participant_status_changed",
            {"participant_name": "Alice", "status": "speaking"},
        ),
        (
            "on_tool_call",
            {"name": "web_search", "status": "started"},
            "semantic:tool_call",
            {"name": "web_search", "status": "started"},
        ),
    ],
)
async def test_server_meeting_callback_broadcasts_semantic_events(
    method_name: str,
    kwargs: dict[str, object],
    expected_type: str,
    expected_data: dict[str, object],
) -> None:
    connection_manager = _connection_manager()
    callback = ServerMeetingCallback(connection_manager)

    await getattr(callback, method_name)(**kwargs)

    connection_manager.broadcast.assert_awaited_once()
    payload = json.loads(connection_manager.broadcast.await_args.args[0])
    assert payload["type"] == expected_type
    assert payload["data"] == expected_data
    _assert_timestamp_isoformat(payload["timestamp"])


@pytest.mark.asyncio
async def test_server_meeting_callback_can_disable_semantic_broadcasts() -> None:
    connection_manager = _connection_manager()
    callback = ServerMeetingCallback(connection_manager, broadcast_semantic=False)

    await callback.on_token(content="토큰", speaker="Alice", is_delegated=False)

    connection_manager.broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_server_meeting_callback_keeps_raw_event_broadcast_when_semantic_disabled() -> None:
    connection_manager = _connection_manager()
    callback = ServerMeetingCallback(connection_manager, broadcast_semantic=False)

    await callback.on_raw_event({"event": "on_chain_start", "data": {"foo": "bar"}})

    connection_manager.broadcast.assert_awaited_once()
    payload = json.loads(connection_manager.broadcast.await_args.args[0])
    assert payload["type"] == "on_chain_start"
    assert payload["data"] == {"foo": "bar"}
    _assert_timestamp_isoformat(payload["timestamp"])
