"""WebSocket client for server-backed TUI mode."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any

from websockets import connect
from websockets.exceptions import ConnectionClosed

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

if TYPE_CHECKING:
    from doorae.interfaces.tui import MeetingTuiApp


class ServerEventClient:
    """Receive semantic room events and adapt them into existing TUI messages."""

    def __init__(self, ws_url: str, username: str, app: "MeetingTuiApp") -> None:
        self._ws_url = ws_url
        self._username = username
        self._app = app
        self._websocket: Any = None
        self._ready = asyncio.Event()
        self.connected = asyncio.Event()
        self._pending_speakers: list[str] = []

    async def run(self) -> None:
        self._ready.clear()
        self.connected.clear()
        self._pending_speakers = []
        try:
            async with connect(self._ws_url) as websocket:
                self._websocket = websocket
                self.connected.set()
                self._ready.set()

                while True:
                    try:
                        raw_message = await websocket.recv()
                    except ConnectionClosed as exc:
                        self._emit_error(f"서버 연결이 종료되었습니다: {exc}")
                        return
                    except StopAsyncIteration:
                        self._emit_error("서버 연결이 종료되었습니다.")
                        return

                    if not isinstance(raw_message, str):
                        continue
                    try:
                        event = json.loads(raw_message)
                    except json.JSONDecodeError:
                        continue
                    await self._dispatch_event(event)
        except OSError as exc:
            self._emit_error(f"서버에 연결할 수 없습니다: {exc}")
        except Exception as exc:
            self._emit_error(f"서버 연결 오류: {exc}")
        finally:
            self._websocket = None
            self.connected.clear()
            self._ready.set()
            self._pending_speakers = []

    async def wait_until_connected(self, timeout: float | None = None) -> bool:
        try:
            if timeout is None:
                await self._ready.wait()
            else:
                await asyncio.wait_for(self._ready.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return False
        return self.connected.is_set()

    async def send_input(self, content: str) -> None:
        if self._websocket is None:
            self._emit_error("서버에 아직 연결되지 않았습니다.")
            return
        try:
            await self._websocket.send(json.dumps({"content": content}))
        except ConnectionClosed as exc:
            self._emit_error(f"입력 전송 중 연결이 종료되었습니다: {exc}")
        except Exception as exc:
            self._emit_error(f"입력 전송 실패: {exc}")

    async def close(self) -> None:
        if self._websocket is not None:
            await self._websocket.close()

    async def _dispatch_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if not isinstance(event_type, str):
            return

        if event_type == "error":
            data = event.get("data", {})
            if isinstance(data, dict):
                message = data.get("error")
                if isinstance(message, str) and message:
                    self._emit_error(message)
            return

        if not event_type.startswith("semantic:"):
            return

        data = event.get("data", {})
        if not isinstance(data, dict):
            data = {}
        semantic_type = event_type.removeprefix("semantic:")

        if semantic_type == "speaker_changed":
            speaker = data.get("speaker")
            if isinstance(speaker, str) and speaker:
                self._app.post_message(
                    SpeakerChanged(
                        speaker=speaker,
                        pending=list(self._pending_speakers),
                        is_delegated=bool(data.get("is_delegated", False)),
                    )
                )
            return

        if semantic_type == "token":
            content = data.get("content")
            speaker = data.get("speaker")
            if isinstance(content, str) and isinstance(speaker, str) and content:
                self._app.post_message(
                    TokenStreamed(
                        token=content,
                        agent_name=speaker,
                        is_delegated=bool(data.get("is_delegated", False)),
                    )
                )
            return

        if semantic_type == "turn_completed":
            speaker = data.get("speaker")
            if isinstance(speaker, str) and speaker:
                self._app.post_message(
                    TurnCompleted(
                        speaker=speaker,
                        is_delegated=bool(data.get("is_delegated", False)),
                    )
                )
            return

        if semantic_type == "human_turn_started":
            username = data.get("username")
            if isinstance(username, str) and username:
                self._app.post_message(HumanTurnStarted(username=username))
            return

        if semantic_type == "agenda_updated":
            agendas = data.get("agendas")
            current_idx = data.get("current_idx")
            if isinstance(agendas, list) and isinstance(current_idx, int):
                self._app.post_message(AgendaUpdated(agendas=agendas, current_idx=current_idx))
            return

        if semantic_type == "meeting_ended":
            agendas = data.get("agendas")
            speaker_counts = data.get("speaker_counts")
            if isinstance(agendas, list) and isinstance(speaker_counts, dict):
                self._app.post_message(MeetingEnded(agendas=agendas, speaker_counts=speaker_counts))
            return

        if semantic_type == "pending_speakers_changed":
            pending = data.get("pending_speakers")
            if isinstance(pending, list):
                self._pending_speakers = [speaker for speaker in pending if isinstance(speaker, str)]
            return

        if semantic_type == "participant_status_changed":
            participant_name = data.get("participant_name")
            status = data.get("status")
            if isinstance(participant_name, str) and isinstance(status, str):
                self._app.post_message(
                    ParticipantStatusChanged(participant_name=participant_name, status=status)
                )
            return

        if semantic_type == "tool_call":
            tool_name = data.get("name")
            status = data.get("status")
            if not isinstance(tool_name, str) or not isinstance(status, str):
                return
            if status == "started":
                self._app.post_message(ToolCallStarted(tool_name=tool_name))
            elif status == "ended":
                self._app.post_message(ToolCallEnded(tool_name=tool_name))

    def _emit_error(self, message: str) -> None:
        self._app.post_message(StreamError(message))
