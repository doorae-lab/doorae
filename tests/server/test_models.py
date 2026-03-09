"""서버 모델 테스트."""

from datetime import datetime
import pytest
from pydantic import ValidationError
from doorae.server.models import RoomCreate, RoomInfo


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
