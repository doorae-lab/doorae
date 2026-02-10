"""Room 테스트."""

import pytest
import asyncio
from thetable.server.room import Room
from thetable.server.room_manager import RoomManager, get_room_manager


def test_room_creation():
    """Room 생성 테스트."""
    room = Room(room_id="test-123", name="Test Room", agenda="Test Agenda")

    assert room.id == "test-123"
    assert room.name == "Test Room"
    assert room.agenda == "Test Agenda"
    assert room.created_at is not None
    assert room.connection_manager is not None
    assert room.input_queues == {}


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
