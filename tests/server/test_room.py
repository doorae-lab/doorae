"""Room 테스트."""

import json

import asyncio
import pytest
from doorae.core.profile import AgentProfile
from doorae.interfaces.engine import MeetingEngineRuntimeState
from doorae.server.events import format_state_snapshot_event
from doorae.server.room import Room
from doorae.server.room_manager import RoomManager, get_room_manager


class MockConnectionManager:
    """테스트용 ConnectionManager mock."""

    def __init__(self):
        self.connections: dict[str, object] = {}
        self.broadcasts: list[str] = []
        self.personal_messages: list[tuple[str, str]] = []  # (message, username)

    async def connect(self, username, websocket):
        self.connections[username] = websocket

    def disconnect(self, username):
        self.connections.pop(username, None)

    async def broadcast(self, message):
        self.broadcasts.append(message)

    async def send_personal_message(self, message, username):
        self.personal_messages.append((message, username))

    def get_connection_count(self):
        return len(self.connections)

class DummyStreamingTask:
    def done(self) -> bool:
        return False


class DummyEngine:
    def __init__(
        self,
        runtime_state: MeetingEngineRuntimeState,
        top_profiles: dict[str, AgentProfile],
    ) -> None:
        self.runtime_state = runtime_state
        self.setup_state = type(
            "SetupState",
            (),
            {"top_profiles": top_profiles},
        )()


class MockParticipantRegistry:
    def __init__(self) -> None:
        self.profiles: dict[str, AgentProfile] = {}
        self.added: list[AgentProfile] = []
        self.removed: list[str] = []

    def add(self, profile: AgentProfile) -> None:
        self.profiles[profile.name] = profile
        self.added.append(profile)

    def remove(self, name: str) -> None:
        self.profiles.pop(name, None)
        self.removed.append(name)


def test_room_creation():
    """Room 생성 테스트."""
    room = Room(room_id="test-123", name="Test Room", agenda="Test Agenda")

    assert room.id == "test-123"
    assert room.name == "Test Room"
    assert room.agenda == "Test Agenda"
    assert room.created_at is not None
    assert room.connection_manager is not None
    assert room.input_queues == {}
    assert room.participant_registry is None


def test_room_get_info():
    """Room 정보 조회 테스트."""
    room = Room(room_id="test-123", name="Test Room")
    info = room.get_info()

    assert info["id"] == "test-123"
    assert info["name"] == "Test Room"
    assert info["agenda"] is None
    assert info["created_at"] is not None
    assert info["participants_count"] == 0


def test_room_create_user_queue():
    """사용자 입력 큐 생성 테스트."""
    room = Room(room_id="test-123", name="Test Room")

    queue = room.create_user_queue("Alice")

    assert isinstance(queue, asyncio.Queue)
    assert room.get_user_queue("Alice") is queue


def test_room_create_user_queue_idempotent():
    """사용자 입력 큐 중복 생성 테스트."""
    room = Room(room_id="test-123", name="Test Room")

    queue1 = room.create_user_queue("Alice")
    queue2 = room.create_user_queue("Alice")

    assert queue1 is queue2


def test_room_remove_user_queue():
    """사용자 입력 큐 제거 테스트."""
    room = Room(room_id="test-123", name="Test Room")
    room.create_user_queue("Alice")

    room.remove_user_queue("Alice")

    assert room.get_user_queue("Alice") is None


def test_room_manager_create_room():
    """RoomManager 회의방 생성 테스트."""
    manager = RoomManager()
    room = manager.create_room(name="Test Room", agenda="Test Agenda")

    assert room.name == "Test Room"
    assert room.agenda == "Test Agenda"
    assert manager.get_room(room.id) is room


def test_room_manager_max_rooms():
    """RoomManager 최대 회의방 수 테스트."""
    manager = RoomManager()
    manager.max_rooms = 2

    manager.create_room("Room 1")
    manager.create_room("Room 2")

    with pytest.raises(ValueError, match="최대 회의방 수"):
        manager.create_room("Room 3")


def test_room_manager_delete_room():
    """RoomManager 회의방 삭제 테스트."""
    manager = RoomManager()
    room = manager.create_room("Test Room")

    result = manager.delete_room(room.id)

    assert result is True
    assert manager.get_room(room.id) is None


def test_room_manager_delete_nonexistent_room():
    """RoomManager 존재하지 않는 회의방 삭제 테스트."""
    manager = RoomManager()

    result = manager.delete_room("nonexistent")

    assert result is False


def test_room_manager_list_rooms():
    """RoomManager 회의방 목록 조회 테스트."""
    manager = RoomManager()
    room1 = manager.create_room("Room 1")
    room2 = manager.create_room("Room 2")

    rooms = manager.list_rooms()

    assert len(rooms) == 2
    room_ids = [r["id"] for r in rooms]
    assert room1.id in room_ids
    assert room2.id in room_ids


def test_get_room_manager_singleton():
    """RoomManager 싱글톤 테스트."""
    manager1 = get_room_manager()
    manager2 = get_room_manager()

    assert manager1 is manager2


# ── 활성 사용자 추적 테스트 ──


def test_room_initial_current_active_human_is_none():
    """Room 생성 시 _current_active_human은 None."""
    room = Room(room_id="test", name="Test")
    assert room._current_active_human is None


def test_room_set_current_active_human():
    """set_current_active_human으로 활성 사용자 설정."""
    room = Room(room_id="test", name="Test")
    room.set_current_active_human("Alice")
    assert room._current_active_human == "Alice"


def test_room_clear_current_active_human():
    """clear_current_active_human으로 활성 사용자 초기화."""
    room = Room(room_id="test", name="Test")
    room.set_current_active_human("Alice")
    room.clear_current_active_human()
    assert room._current_active_human is None


# ── handle_message 입력 차례 검증 테스트 ──


@pytest.mark.asyncio
async def test_handle_message_rejects_non_active_user():
    """활성 사용자가 아닌 사용자의 입력은 거부."""
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.set_current_active_human("Alice")
    room.create_user_queue("Alice")
    room.create_user_queue("Bob")

    await room.handle_message("Bob", json.dumps({"content": "hello"}))

    # Bob의 큐는 비어있어야 함 (거부됨)
    assert room.get_user_queue("Bob").empty()
    # Bob에게 에러 메시지 전송
    assert len(room.connection_manager.personal_messages) == 1
    assert room.connection_manager.personal_messages[0][1] == "Bob"
    error_data = json.loads(room.connection_manager.personal_messages[0][0])
    assert error_data["type"] == "error"
    assert "차례가 아닙니다" in error_data["data"]["error"]
    # 브로드캐스트는 발생하지 않아야 함
    assert len(room.connection_manager.broadcasts) == 0


@pytest.mark.asyncio
async def test_handle_message_accepts_active_user():
    """활성 사용자의 입력은 정상 처리."""
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.set_current_active_human("Alice")
    room.create_user_queue("Alice")

    await room.handle_message("Alice", json.dumps({"content": "hello"}))

    # Alice의 큐에 입력이 추가되어야 함
    assert not room.get_user_queue("Alice").empty()
    content = await room.get_user_queue("Alice").get()
    assert content == "hello"
    # 활성 사용자 초기화
    assert room._current_active_human is None
    # 메시지 브로드캐스트
    assert len(room.connection_manager.broadcasts) == 1


@pytest.mark.asyncio
async def test_handle_message_no_active_human_allows_all():
    """활성 사용자가 없으면 모든 사용자의 입력 허용."""
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.create_user_queue("Bob")

    await room.handle_message("Bob", json.dumps({"content": "hello"}))

    assert not room.get_user_queue("Bob").empty()
    content = await room.get_user_queue("Bob").get()
    assert content == "hello"
    assert len(room.connection_manager.broadcasts) == 1


@pytest.mark.asyncio
async def test_handle_message_rejects_non_active_user_no_broadcast():
    """거부된 메시지는 브로드캐스트되지 않아야 함."""
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.set_current_active_human("Alice")
    room.create_user_queue("Alice")
    room.create_user_queue("Bob")

    await room.handle_message("Bob", json.dumps({"content": "나도 의견 있어요"}))

    # 브로드캐스트 없음
    assert len(room.connection_manager.broadcasts) == 0
    # 활성 사용자 변경 없음
    assert room._current_active_human == "Alice"


# ── join 참가자 목록 전송 테스트 ──


@pytest.mark.asyncio
async def test_join_sends_participants_list_to_new_user():
    """새 입장자에게 기존 참가자 목록이 전송되는지 테스트."""
    room = Room(room_id="test", name="Test")
    mock_cm = MockConnectionManager()
    mock_cm.connections["Alice"] = "ws_alice"  # Pre-existing user
    room.connection_manager = mock_cm

    await room.join("Bob", "ws_bob")

    # Check personal message sent to Bob with Alice's info
    assert len(mock_cm.personal_messages) >= 1
    msg = json.loads(mock_cm.personal_messages[0][0])
    assert msg["type"] == "semantic:participants_list"
    assert mock_cm.personal_messages[0][1] == "Bob"
    participants = msg["data"]["participants"]
    assert any(p["username"] == "Alice" for p in participants)


@pytest.mark.asyncio
async def test_join_broadcasts_user_joined():
    """기존 참가자에게 새 입장자 알림이 브로드캐스트되는지 테스트."""
    room = Room(room_id="test", name="Test")
    mock_cm = MockConnectionManager()
    room.connection_manager = mock_cm

    await room.join("Alice", "ws_alice")

    # Find user_joined broadcast
    user_joined_broadcasts = [
        json.loads(b) for b in mock_cm.broadcasts
        if "user_joined" in b
    ]
    assert len(user_joined_broadcasts) == 1
    assert user_joined_broadcasts[0]["data"]["username"] == "Alice"


@pytest.mark.asyncio
async def test_join_adds_runtime_profile_when_workflow_running():
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.workflow = object()
    room.participant_registry = MockParticipantRegistry()

    await room.join("Alice", "ws_alice")

    assert "Alice" in room.input_queues
    assert room.participant_registry.added[0].name == "Alice"
    assert room.participant_registry.added[0].is_human is True


@pytest.mark.asyncio
async def test_leave_unblocks_waiting_human_and_removes_registry_entry():
    room = Room(room_id="test", name="Test")
    room.connection_manager = MockConnectionManager()
    room.workflow = object()
    room.participant_registry = MockParticipantRegistry()
    queue = room.create_user_queue("Alice")
    room.participant_registry.add(
        AgentProfile(
            name="Alice",
            role="participant",
            responsibilities=["참여"],
            expertise=["일반"],
            is_human=True,
        )
    )
    room.set_current_active_human("Alice")

    await room.leave("Alice")

    assert queue.get_nowait() is None
    assert room._current_active_human is None
    assert room.participant_registry.removed == ["Alice"]
    assert room.get_user_queue("Alice") is None


@pytest.mark.asyncio
async def test_first_user_gets_empty_participants_list():
    """첫 번째 입장자에게는 빈 participants_list가 전송되지 않는지 테스트."""
    room = Room(room_id="test", name="Test")
    mock_cm = MockConnectionManager()
    room.connection_manager = mock_cm

    await room.join("Alice", "ws_alice")

    # No personal message for participants_list (no existing participants)
    participants_msgs = [
        pm for pm in mock_cm.personal_messages
        if "participants_list" in pm[0]
    ]
    assert len(participants_msgs) == 0


def test_format_state_snapshot_event_serializes_runtime_state() -> None:
    runtime_state = MeetingEngineRuntimeState(
        current_speaker="Alice",
        current_agenda_idx=1,
        agendas=[{"title": "예산", "status": "in_progress"}],
        pending_speakers=["Bob"],
        speaker_counts={"Alice": 2},
        participant_statuses={"Alice": "speaking", "Bob": "idle"},
    )
    top_profiles = {
        "Alice": AgentProfile(
            name="Alice",
            role="participant",
            responsibilities=["회의 참여"],
            expertise=["예산"],
            is_human=True,
        )
    }

    event = format_state_snapshot_event(runtime_state, top_profiles)

    assert event["type"] == "semantic:state_snapshot"
    assert event["data"]["current_speaker"] == "Alice"
    assert event["data"]["current_agenda_idx"] == 1
    assert event["data"]["pending_speakers"] == ["Bob"]
    assert event["data"]["speaker_counts"] == {"Alice": 2}
    assert event["data"]["participant_statuses"] == {"Alice": "speaking", "Bob": "idle"}
    assert event["data"]["top_profiles"]["Alice"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_join_sends_state_snapshot_when_workflow_is_running():
    room = Room(room_id="test", name="Test")
    mock_cm = MockConnectionManager()
    mock_cm.connections["Alice"] = "ws_alice"
    room.connection_manager = mock_cm
    room._streaming_task = DummyStreamingTask()
    room._engine = DummyEngine(
        runtime_state=MeetingEngineRuntimeState(
            current_speaker="Alice",
            current_agenda_idx=0,
            agendas=[{"title": "예산", "status": "in_progress"}],
            pending_speakers=["Bob"],
            speaker_counts={"Alice": 1},
            participant_statuses={"Alice": "speaking", "Bob": "idle"},
        ),
        top_profiles={
            "Alice": AgentProfile(
                name="Alice",
                role="participant",
                responsibilities=["회의 참여"],
                expertise=["예산"],
                is_human=True,
            )
        },
    )

    await room.join("Bob", "ws_bob")

    personal_messages = [json.loads(message) for message, username in mock_cm.personal_messages if username == "Bob"]
    message_types = [message["type"] for message in personal_messages]
    assert message_types == [
        "semantic:participants_list",
        "semantic:state_snapshot",
    ]
    snapshot = personal_messages[1]
    assert snapshot["data"]["current_speaker"] == "Alice"
    assert snapshot["data"]["pending_speakers"] == ["Bob"]
    assert snapshot["data"]["participant_statuses"]["Alice"] == "speaking"


@pytest.mark.asyncio
async def test_join_skips_state_snapshot_when_workflow_is_not_running():
    room = Room(room_id="test", name="Test")
    mock_cm = MockConnectionManager()
    mock_cm.connections["Alice"] = "ws_alice"
    room.connection_manager = mock_cm

    await room.join("Bob", "ws_bob")

    personal_messages = [json.loads(message) for message, username in mock_cm.personal_messages if username == "Bob"]
    assert [message["type"] for message in personal_messages] == [
        "semantic:participants_list",
    ]
