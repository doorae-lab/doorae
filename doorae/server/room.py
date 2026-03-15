"""회의방 클래스."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import WebSocket
from doorae.core.profile import AgentProfile
from doorae.interfaces.engine import MeetingEngine
from doorae.server.connection_manager import ConnectionManager
from doorae.server.events import (
    event_to_dict,
    format_semantic_event,
    format_message_event,
    format_error_event,
    format_state_snapshot_event,
    format_system_event,
)

logger = logging.getLogger(__name__)


def _strip_llm(profile_data: dict[str, Any]) -> dict[str, Any]:
    """Remove llm configuration recursively before broadcasting profile data."""
    cleaned = dict(profile_data)
    cleaned.pop("llm", None)

    agents = cleaned.get("agents")
    if isinstance(agents, list):
        cleaned["agents"] = [
            _strip_llm(child) if isinstance(child, dict) else child
            for child in agents
        ]
    return cleaned


def _serialize_top_profiles(top_profiles: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Serialize top profiles for WebSocket delivery without embedded llm config."""
    return {
        name: _strip_llm(profile.model_dump())
        for name, profile in top_profiles.items()
    }


def _build_runtime_human_profile(username: str) -> AgentProfile:
    return AgentProfile(
        name=username,
        role="participant",
        responsibilities=["회의 참여", "의견 제시"],
        expertise=["일반"],
        is_human=True,
    )


class ServerMeetingCallback:
    """Broadcast raw MeetingEngine events to all room participants."""

    def __init__(
        self,
        connection_manager: ConnectionManager,
        broadcast_raw: bool = True,
        broadcast_semantic: bool = True,
        room: "Room | None" = None,
    ) -> None:
        self._connection_manager = connection_manager
        self._broadcast_raw = broadcast_raw
        self._broadcast_semantic = broadcast_semantic
        self._room = room

    async def on_raw_event(self, event: dict) -> None:
        if not self._broadcast_raw:
            return
        await self._connection_manager.broadcast(
            json.dumps(event_to_dict(event)),
            channel="raw",
        )

    async def _broadcast_event(self, event_type: str, **payload: object) -> None:
        if not self._broadcast_semantic:
            return
        await self._connection_manager.broadcast(
            json.dumps(format_semantic_event(event_type, **payload)),
            channel="semantic",
        )

    async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None:
        await self._broadcast_event(
            "speaker_changed",
            speaker=speaker,
            is_delegated=is_delegated,
        )

    async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None:
        await self._broadcast_event(
            "token",
            content=content,
            speaker=speaker,
            is_delegated=is_delegated,
        )

    async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None:
        # human turn이 완료되면 활성 사용자 초기화 (타임아웃 등 입력 없이 넘어간 경우 대비)
        if (
            not is_delegated
            and self._room is not None
            and self._room._current_active_human == speaker
        ):
            self._room.clear_current_active_human()
        await self._broadcast_event(
            "turn_completed",
            speaker=speaker,
            is_delegated=is_delegated,
        )

    async def on_human_turn_started(self, username: str) -> None:
        if self._room is not None:
            self._room.set_current_active_human(username)
        await self._broadcast_event("human_turn_started", username=username)

    async def on_agenda_updated(
        self,
        agendas: list[dict],
        current_idx: int,
    ) -> None:
        await self._broadcast_event(
            "agenda_updated",
            agendas=agendas,
            current_idx=current_idx,
        )

    async def on_meeting_ended(
        self,
        agendas: list[dict],
        speaker_counts: dict[str, int],
    ) -> None:
        await self._broadcast_event(
            "meeting_ended",
            agendas=agendas,
            speaker_counts=speaker_counts,
        )

    async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None:
        await self._broadcast_event(
            "pending_speakers_changed",
            pending_speakers=pending_speakers,
        )

    async def on_participant_status_changed(self, participant_name: str, status: str) -> None:
        await self._broadcast_event(
            "participant_status_changed",
            participant_name=participant_name,
            status=status,
        )

    async def on_tool_call(self, name: str, status: str) -> None:
        await self._broadcast_event("tool_call", name=name, status=status)


class Room:
    """회의방 클래스.

    Attributes:
        id: 회의방 ID
        name: 회의방 이름
        agenda: 회의 안건
        created_at: 생성 시간
        connection_manager: WebSocket 연결 관리자
        input_queues: username별 입력 큐 딕셔너리
        workflow: LangGraph 워크플로우 (선택적)
        _streaming_task: 워크플로우 스트리밍 백그라운드 태스크
    """

    def __init__(
        self,
        room_id: str,
        name: str,
        agenda: Optional[str] = None,
    ):
        """초기화.

        Args:
            room_id: 회의방 ID
            name: 회의방 이름
            agenda: 회의 안건 (선택적)
        """
        self.id = room_id
        self.name = name
        self.agenda = agenda
        self.created_at = datetime.now()
        self.connection_manager = ConnectionManager()
        self.input_queues: dict[str, asyncio.Queue] = {}
        self.workflow = None
        self.participant_registry = None
        self._streaming_task: Optional[asyncio.Task] = None
        self._engine: MeetingEngine | None = None
        self._current_active_human: str | None = None

    def get_info(self) -> dict:
        """회의방 정보 반환.

        Returns:
            회의방 정보 딕셔너리
        """
        return {
            "id": self.id,
            "name": self.name,
            "agenda": self.agenda,
            "created_at": self.created_at,
            "participants_count": self.connection_manager.get_connection_count(),
        }

    def create_user_queue(self, username: str) -> asyncio.Queue:
        """사용자 입력 큐 생성.

        Args:
            username: 사용자 이름

        Returns:
            생성된 asyncio.Queue
        """
        if username not in self.input_queues:
            self.input_queues[username] = asyncio.Queue()
        return self.input_queues[username]

    def get_user_queue(self, username: str) -> Optional[asyncio.Queue]:
        """사용자 입력 큐 반환.

        Args:
            username: 사용자 이름

        Returns:
            입력 큐 또는 None
        """
        return self.input_queues.get(username)

    def remove_user_queue(self, username: str):
        """사용자 입력 큐 제거.

        Args:
            username: 사용자 이름
        """
        if username in self.input_queues:
            del self.input_queues[username]

    def set_current_active_human(self, username: str) -> None:
        """현재 입력 차례인 사용자 설정.

        Args:
            username: 활성 사용자 이름
        """
        self._current_active_human = username

    def clear_current_active_human(self) -> None:
        """현재 활성 사용자 초기화."""
        self._current_active_human = None

    async def join(self, username: str, websocket: WebSocket, raw_events: bool = True):
        """사용자 입장 처리.

        연결 수락 후 기존 참가자 목록을 새 입장자에게 전송하고,
        구조화된 입장 이벤트와 시스템 메시지를 브로드캐스트합니다.

        Args:
            username: 사용자 이름
            websocket: WebSocket 연결
        """
        is_reconnecting = username in self.input_queues
        self.create_user_queue(username)
        await self.connection_manager.connect(
            username,
            websocket,
            raw_events=raw_events,
        )

        if self.workflow is not None and self.participant_registry is not None:
            self.create_user_queue(username)
            add_profile = getattr(self.participant_registry, "add", None)
            if callable(add_profile):
                add_profile(_build_runtime_human_profile(username))

        # Send existing participant list to the newly joined user
        existing_usernames = [
            name for name in self.connection_manager.connections
            if name != username
        ]
        if existing_usernames:
            participants_event = format_semantic_event(
                "participants_list",
                participants=[
                    {"username": name, "role": "participant"}
                    for name in existing_usernames
                ],
            )
            await self.connection_manager.send_personal_message(
                json.dumps(participants_event), username
            )

        snapshot_event = self._build_state_snapshot_event()
        if snapshot_event is not None:
            await self.connection_manager.send_personal_message(
                json.dumps(snapshot_event),
                username,
            )

        if is_reconnecting:
            online_event = format_semantic_event(
                "participant_status_changed",
                participant_name=username,
                status="idle",
            )
            await self.connection_manager.broadcast(json.dumps(online_event))
            reconnect_event = format_system_event(f"{username}님이 다시 연결되었습니다.")
            await self.connection_manager.broadcast(json.dumps(reconnect_event))
            return

        # Broadcast structured join event to all (including new joiner)
        user_joined_event = format_semantic_event(
            "user_joined",
            username=username,
            role="participant",
        )
        await self.connection_manager.broadcast(json.dumps(user_joined_event))

        # Keep existing system message for chat display
        join_event = format_system_event(f"{username}님이 입장했습니다.")
        await self.connection_manager.broadcast(json.dumps(join_event))

    async def disconnect(self, username: str):
        """연결만 해제하고 입력 큐는 보존한다."""
        self.connection_manager.disconnect(username)
        offline_event = format_semantic_event(
            "participant_status_changed",
            participant_name=username,
            status="offline",
        )
        await self.connection_manager.broadcast(json.dumps(offline_event))
        disconnect_event = format_system_event(
            f"{username}님의 연결이 끊겼습니다. 재연결을 기다립니다."
        )
        await self.connection_manager.broadcast(json.dumps(disconnect_event))

    async def leave(self, username: str):
        """사용자 퇴장 처리.

        연결 해제, 큐 정리 후 퇴장 메시지를 브로드캐스트합니다.

        Args:
            username: 사용자 이름
        """
        if self.workflow is not None:
            queue = self.get_user_queue(username)
            if queue is not None:
                await queue.put(None)

            if self._current_active_human == username:
                self.clear_current_active_human()

            if self.participant_registry is not None:
                remove_profile = getattr(self.participant_registry, "remove", None)
                if callable(remove_profile):
                    remove_profile(username)

        await self.disconnect(username)
        self.remove_user_queue(username)
        leave_event = format_system_event(f"{username}님이 퇴장했습니다.")
        await self.connection_manager.broadcast(json.dumps(leave_event))

    def _build_state_snapshot_event(self) -> dict[str, Any] | None:
        """현재 회의 상태를 신규 접속자에게 보낼 snapshot 이벤트로 구성한다."""
        if self._engine is None:
            return None
        if self._streaming_task is None or self._streaming_task.done():
            return None

        setup_state = self._engine.setup_state
        top_profiles = (
            _serialize_top_profiles(setup_state.top_profiles)
            if setup_state is not None
            else {}
        )
        return format_state_snapshot_event(
            self._engine.runtime_state,
            top_profiles=top_profiles,
        )

    async def handle_message(self, username: str, data: str):
        """메시지 처리.

        JSON 파싱 후 사용자 입력 큐에 추가하고 브로드캐스트합니다.
        파싱 실패 시 발신자에게 에러 메시지를 전송합니다.

        Args:
            username: 발신자 이름
            data: 수신한 원본 텍스트 데이터
        """
        try:
            message_data = json.loads(data)
        except json.JSONDecodeError:
            error_event = format_error_event("잘못된 JSON 형식입니다.")
            await self.connection_manager.send_personal_message(
                json.dumps(error_event), username
            )
            return

        content = message_data.get("content", "")

        # 활성 사용자가 아닌 사용자의 입력 거부
        if (
            self._current_active_human is not None
            and username != self._current_active_human
        ):
            error_event = format_error_event("현재 입력할 수 있는 차례가 아닙니다.")
            await self.connection_manager.send_personal_message(
                json.dumps(error_event), username
            )
            return

        # 사용자 입력 큐에 추가 (워크플로우가 대기 중이면 전달됨)
        queue = self.get_user_queue(username)
        if queue is not None:
            await queue.put(content)

        # 활성 사용자의 입력 처리 후 초기화
        if self._current_active_human == username:
            self._current_active_human = None

        # 사용자 메시지를 참가자에게 브로드캐스트
        message_event = format_message_event(content=content, sender=username)
        await self.connection_manager.broadcast(json.dumps(message_event))

    async def start_workflow_streaming(
        self,
        workflow=None,
        initial_state: dict | None = None,
        config: dict | None = None,
        engine: MeetingEngine | None = None,
    ):
        """워크플로우 스트리밍을 백그라운드 태스크로 시작.

        astream_events로 워크플로우를 실행하고, 각 이벤트를 JSON 변환하여
        Room의 모든 참가자에게 브로드캐스트합니다.

        Args:
            workflow: 컴파일된 LangGraph 워크플로우
            initial_state: 워크플로우 초기 상태
            config: LangGraph 실행 설정
            engine: 공통 MeetingEngine 인스턴스
        """
        if engine is not None:
            self.workflow = engine
            if engine.setup_state is not None:
                self.participant_registry = getattr(
                    engine.setup_state,
                    "participant_registry",
                    None,
                )
            self._streaming_task = asyncio.create_task(self._stream_engine_events(engine))
            return

        if workflow is None or initial_state is None or config is None:
            raise ValueError("workflow, initial_state, config 또는 engine이 필요합니다.")

        self.workflow = workflow
        self._streaming_task = asyncio.create_task(
            self._stream_workflow_events(workflow, initial_state, config)
        )

    async def _stream_workflow_events(self, workflow, state: dict, config: dict):
        """워크플로우 이벤트를 스트리밍하여 브로드캐스트.

        Args:
            workflow: 컴파일된 LangGraph 워크플로우
            state: 초기 상태
            config: LangGraph 실행 설정
        """
        try:
            async for event in workflow.astream_events(
                state, config=config, version="v2"
            ):
                ws_event = event_to_dict(event)
                await self.connection_manager.broadcast(json.dumps(ws_event))
        except asyncio.CancelledError:
            logger.info(f"Workflow streaming cancelled for room {self.id}")
        except Exception as e:
            logger.error(f"Workflow streaming error in room {self.id}: {e}")
            error_event = format_error_event(f"워크플로우 오류: {e}")
            await self.connection_manager.broadcast(json.dumps(error_event))

    async def _stream_engine_events(self, engine: MeetingEngine):
        """MeetingEngine 이벤트를 스트리밍하여 브로드캐스트."""
        try:
            self._engine = engine
            # Ensure setup is complete and broadcast profiles to clients
            setup_state = engine.setup_state
            if setup_state is None:
                setup_state = engine.setup()
            self.participant_registry = getattr(setup_state, "participant_registry", None)

            top_profiles_data = _serialize_top_profiles(setup_state.top_profiles)
            profiles_event = format_semantic_event(
                "agent_profiles",
                top_profiles=top_profiles_data,
            )
            await self.connection_manager.broadcast(json.dumps(profiles_event))

            await engine.run(ServerMeetingCallback(self.connection_manager, room=self))
        except asyncio.CancelledError:
            logger.info(f"Workflow streaming cancelled for room {self.id}")
        except Exception as e:
            logger.error(f"Workflow streaming error in room {self.id}: {e}")
            error_event = format_error_event(f"워크플로우 오류: {e}")
            await self.connection_manager.broadcast(json.dumps(error_event))

    async def stop_workflow_streaming(self):
        """워크플로우 스트리밍 태스크를 중지.

        cancel 후 완료를 대기합니다.
        """
        if self._streaming_task is not None and not self._streaming_task.done():
            self._streaming_task.cancel()
            try:
                await self._streaming_task
            except asyncio.CancelledError:
                pass
            self._streaming_task = None
        self._engine = None
        self.workflow = None
        self.participant_registry = None
