"""서버 모델 테스트."""

from datetime import datetime
import pytest
from pydantic import ValidationError
from thetable.server.models import RoomCreate, RoomInfo, WSMessage, WSResponse


def test_room_create_valid():
    """RoomCreate 정상 생성 테스트."""
    room = RoomCreate(name="Test Room", agenda="Test Agenda")
    assert room.name == "Test Room"
    assert room.agenda == "Test Agenda"


def test_room_create_without_agenda():
    """RoomCreate agenda 없이 생성 테스트."""
    room = RoomCreate(name="Test Room")
    assert room.name == "Test Room"
    assert room.agenda is None


def test_room_create_validation_error():
    """RoomCreate 유효성 검사 실패 테스트."""
    with pytest.raises(ValidationError):
        RoomCreate(name="")  # 빈 이름


def test_room_info_serialization():
    """RoomInfo 직렬화 테스트."""
    now = datetime.now()
    room = RoomInfo(
        id="room-123",
        name="Test Room",
        agenda="Test Agenda",
        created_at=now,
        participants_count=5,
    )
    data = room.model_dump()
    assert data["id"] == "room-123"
    assert data["name"] == "Test Room"
    assert data["agenda"] == "Test Agenda"
    assert data["created_at"] == now
    assert data["participants_count"] == 5


def test_ws_message_valid():
    """WSMessage 정상 생성 테스트."""
    msg = WSMessage(
        type="chat",
        content="Hello",
        sender="Alice",
        timestamp=datetime.now(),
    )
    assert msg.type == "chat"
    assert msg.content == "Hello"
    assert msg.sender == "Alice"
    assert msg.timestamp is not None


def test_ws_message_without_timestamp():
    """WSMessage timestamp 없이 생성 테스트."""
    msg = WSMessage(type="chat", content="Hello", sender="Alice")
    assert msg.type == "chat"
    assert msg.content == "Hello"
    assert msg.sender == "Alice"
    assert msg.timestamp is None


def test_ws_response_auto_timestamp():
    """WSResponse 자동 timestamp 생성 테스트."""
    before = datetime.now()
    resp = WSResponse(type="message", data={"content": "test"})
    after = datetime.now()

    assert resp.type == "message"
    assert resp.data == {"content": "test"}
    assert before <= resp.timestamp <= after


def test_ws_response_serialization():
    """WSResponse 직렬화 테스트."""
    resp = WSResponse(
        type="message",
        data={"user": "Alice", "message": "Hello"},
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )
    data = resp.model_dump()
    assert data["type"] == "message"
    assert data["data"]["user"] == "Alice"
    assert data["data"]["message"] == "Hello"
    assert data["timestamp"] == datetime(2024, 1, 1, 12, 0, 0)
