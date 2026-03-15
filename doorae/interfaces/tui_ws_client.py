"""WebSocket client for server-backed TUI mode."""

from __future__ import annotations

import asyncio
import json
import random
from typing import TYPE_CHECKING, Any

from websockets import connect
from websockets.exceptions import ConnectionClosed

from doorae.interfaces.tui import (
    AgendaUpdated,
    AgentProfilesReceived,
    ConnectionStatus,
    ConnectionStatusChanged,
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


INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 30.0
BACKOFF_FACTOR = 2.0
JITTER_FACTOR = 0.1


def _format_connection_closed(exc: ConnectionClosed) -> str:
    """Convert a ConnectionClosed exception into a user-friendly Korean message."""
    rcvd = getattr(exc, "rcvd", None)
    code = getattr(rcvd, "code", None) if rcvd is not None else None
    if code == 1000:
        return "서버 연결이 정상적으로 종료되었습니다."
    if code == 1001:
        return "서버가 종료되었습니다."
    if code == 1006:
        return "서버 연결이 비정상적으로 종료되었습니다. 서버 상태를 확인하세요."
    if code is not None:
        return f"서버 연결이 종료되었습니다 (코드: {code})."
    return "서버 연결이 종료되었습니다."


def _compute_retry_delay(attempt: int) -> float:
    """Return a jittered exponential backoff delay in seconds."""
    capped_attempt = max(attempt - 1, 0)
    base_delay = min(INITIAL_RETRY_DELAY * (BACKOFF_FACTOR**capped_attempt), MAX_RETRY_DELAY)
    jitter = 1 + random.uniform(-JITTER_FACTOR, JITTER_FACTOR)
    return max(0.0, base_delay * jitter)


class ServerEventClient:
    """Receive semantic room events and adapt them into existing TUI messages."""

    def __init__(self, ws_url: str, username: str, app: "MeetingTuiApp") -> None:
        self._ws_url = ws_url
        self._username = username
        self._app = app
        self._websocket: Any = None
        self._ready = asyncio.Event()
        self.connected = asyncio.Event()
        self._stopped = asyncio.Event()
        self._pending_speakers: list[str] = []

    async def run(self) -> None:
        self._ready.clear()
        self.connected.clear()
        self._stopped.clear()
        self._pending_speakers = []
        try:
            attempt = 0
            has_connected = False
            while not self._stopped.is_set():
                should_retry = False
                try:
                    async with connect(self._ws_url) as websocket:
                        self._websocket = websocket
                        self.connected.set()
                        connected_after_retry = attempt > 0
                        if not has_connected:
                            self._ready.set()
                            has_connected = True
                        if connected_after_retry:
                            self._emit_status(ConnectionStatus.CONNECTED)
                        attempt = 0

                        while not self._stopped.is_set():
                            try:
                                raw_message = await websocket.recv()
                            except ConnectionClosed:
                                should_retry = not self._stopped.is_set()
                                break
                            except StopAsyncIteration:
                                should_retry = False
                                break

                            if not isinstance(raw_message, str):
                                continue
                            try:
                                event = json.loads(raw_message)
                            except json.JSONDecodeError:
                                continue
                            await self._dispatch_event(event)
                except OSError:
                    should_retry = not self._stopped.is_set()
                except Exception as exc:
                    self._emit_error(f"서버 연결 오류: {exc}")
                    return
                finally:
                    self._websocket = None
                    self.connected.clear()

                if not should_retry:
                    break

                self._emit_status(ConnectionStatus.DISCONNECTED)
                attempt += 1
                delay = _compute_retry_delay(attempt)
                self._emit_status(
                    ConnectionStatus.RECONNECTING,
                    attempt=attempt,
                    next_retry=delay,
                )
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    continue
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
            self._emit_error(f"입력 전송 중 {_format_connection_closed(exc)}")
        except Exception as exc:
            self._emit_error(f"입력 전송 실패: {exc}")

    async def close(self) -> None:
        await self.stop()

    async def stop(self) -> None:
        self._stopped.set()
        self._ready.set()
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

        if semantic_type == "agent_profiles":
            top_profiles = data.get("top_profiles")
            if isinstance(top_profiles, dict):
                self._app.post_message(
                    AgentProfilesReceived(top_profiles_data=top_profiles)
                )
            return

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

        if semantic_type == "participants_list":
            participants = data.get("participants")
            if isinstance(participants, list):
                for p in participants:
                    if isinstance(p, dict):
                        uname = p.get("username")
                        if isinstance(uname, str) and uname:
                            self._app.post_message(
                                ParticipantStatusChanged(participant_name=uname, status="idle")
                            )
            return

        if semantic_type == "user_joined":
            uname = data.get("username")
            if isinstance(uname, str) and uname:
                self._app.post_message(
                    ParticipantStatusChanged(participant_name=uname, status="idle")
                )
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

    def _emit_status(
        self,
        status: ConnectionStatus,
        attempt: int = 0,
        next_retry: float | None = None,
    ) -> None:
        self._app.post_message(
            ConnectionStatusChanged(
                status=status,
                attempt=attempt,
                next_retry=next_retry,
            )
        )
