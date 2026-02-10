"""Routes 테스트."""

import pytest
from fastapi.testclient import TestClient
from thetable.server.app import create_app
from thetable.server.room_manager import get_room_manager


@pytest.fixture
def client():
    """TestClient 생성."""
    app = create_app()
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_rooms():
    """각 테스트 전후로 회의방 정리."""
    room_manager = get_room_manager()
    room_manager.rooms.clear()
    yield
    room_manager.rooms.clear()


def test_create_room(client):
    """회의방 생성 API 테스트."""
    response = client.post(
        "/api/rooms",
        json={"name": "Test Room", "agenda": "Test Agenda"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Room"
    assert data["agenda"] == "Test Agenda"
    assert "id" in data
    assert "created_at" in data


def test_create_room_without_agenda(client):
    """안건 없이 회의방 생성 테스트."""
    response = client.post(
        "/api/rooms",
        json={"name": "Test Room"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Room"
    assert data["agenda"] is None


def test_list_rooms(client):
    """회의방 목록 조회 API 테스트."""
    # 회의방 2개 생성
    client.post("/api/rooms", json={"name": "Room 1"})
    client.post("/api/rooms", json={"name": "Room 2"})

    response = client.get("/api/rooms")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(r["name"] == "Room 1" for r in data)
    assert any(r["name"] == "Room 2" for r in data)


def test_get_room(client):
    """특정 회의방 조회 API 테스트."""
    # 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Test Room"}
    )
    room_id = create_response.json()["id"]

    # 회의방 조회
    response = client.get(f"/api/rooms/{room_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == room_id
    assert data["name"] == "Test Room"


def test_get_nonexistent_room(client):
    """존재하지 않는 회의방 조회 테스트."""
    response = client.get("/api/rooms/nonexistent")

    assert response.status_code == 404


def test_delete_room(client):
    """회의방 삭제 API 테스트."""
    # 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Test Room"}
    )
    room_id = create_response.json()["id"]

    # 회의방 삭제
    response = client.delete(f"/api/rooms/{room_id}")

    assert response.status_code == 204

    # 삭제 확인
    get_response = client.get(f"/api/rooms/{room_id}")
    assert get_response.status_code == 404


def test_delete_nonexistent_room(client):
    """존재하지 않는 회의방 삭제 테스트."""
    response = client.delete("/api/rooms/nonexistent")

    assert response.status_code == 404


def test_websocket_connection(client):
    """WebSocket 연결 테스트."""
    # 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Test Room"}
    )
    room_id = create_response.json()["id"]

    # WebSocket 연결
    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as websocket:
        # 입장 메시지 수신
        data = websocket.receive_json()
        assert data["type"] == "system"
        assert "Alice" in data["data"]["message"]
        assert "입장" in data["data"]["message"]


def test_websocket_message_broadcast(client):
    """WebSocket 메시지 브로드캐스트 테스트."""
    # 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Test Room"}
    )
    room_id = create_response.json()["id"]

    # 2명 연결
    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as ws1:
        # Alice 입장 메시지 수신
        ws1.receive_json()

        with client.websocket_connect(f"/ws/{room_id}?username=Bob") as ws2:
            # Alice가 Bob 입장 메시지 수신
            data = ws1.receive_json()
            assert data["type"] == "system"
            assert "Bob" in data["data"]["message"]

            # Bob이 자신의 입장 메시지 수신
            data = ws2.receive_json()
            assert data["type"] == "system"
            assert "Bob" in data["data"]["message"]

            # Alice가 메시지 전송
            ws1.send_json({"content": "Hello"})

            # Alice가 자신의 메시지 수신
            data = ws1.receive_json()
            assert data["type"] == "message"
            assert data["data"]["content"] == "Hello"
            assert data["data"]["sender"] == "Alice"

            # Bob도 메시지 수신
            data = ws2.receive_json()
            assert data["type"] == "message"
            assert data["data"]["content"] == "Hello"
            assert data["data"]["sender"] == "Alice"


def test_websocket_nonexistent_room(client):
    """존재하지 않는 회의방 WebSocket 연결 테스트."""
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/nonexistent?username=Alice"):
            pass
