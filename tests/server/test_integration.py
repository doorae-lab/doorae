"""통합 테스트."""

import pytest
import json
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


def test_full_flow_single_user(client):
    """단일 사용자 전체 플로우 테스트."""
    # 1. 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Test Room", "agenda": "Test Agenda"}
    )
    assert create_response.status_code == 201
    room = create_response.json()
    room_id = room["id"]

    # 2. 회의방 목록 확인
    list_response = client.get("/api/rooms")
    assert list_response.status_code == 200
    rooms = list_response.json()
    assert len(rooms) == 1
    assert rooms[0]["id"] == room_id

    # 3. WebSocket 연결 및 메시지 전송
    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as websocket:
        # 입장 메시지 수신
        join_message = websocket.receive_json()
        assert join_message["type"] == "system"
        assert "Alice" in join_message["data"]["message"]

        # 메시지 전송
        websocket.send_json({"content": "Hello, world!"})

        # 메시지 수신 확인
        message = websocket.receive_json()
        assert message["type"] == "message"
        assert message["data"]["content"] == "Hello, world!"
        assert message["data"]["sender"] == "Alice"

    # 4. 회의방 삭제
    delete_response = client.delete(f"/api/rooms/{room_id}")
    assert delete_response.status_code == 204

    # 5. 삭제 확인
    get_response = client.get(f"/api/rooms/{room_id}")
    assert get_response.status_code == 404


def test_full_flow_multiple_users(client):
    """다중 사용자 전체 플로우 테스트."""
    # 1. 회의방 생성
    create_response = client.post(
        "/api/rooms",
        json={"name": "Multi User Room"}
    )
    room_id = create_response.json()["id"]

    # 2. 2명의 사용자 동시 연결
    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as ws_alice:
        # Alice 입장 메시지
        alice_join = ws_alice.receive_json()
        assert alice_join["type"] == "system"

        with client.websocket_connect(f"/ws/{room_id}?username=Bob") as ws_bob:
            # Alice가 Bob 입장 메시지 수신
            bob_join_for_alice = ws_alice.receive_json()
            assert bob_join_for_alice["type"] == "system"
            assert "Bob" in bob_join_for_alice["data"]["message"]

            # Bob이 자신의 입장 메시지 수신
            bob_join = ws_bob.receive_json()
            assert bob_join["type"] == "system"

            # 3. Alice가 메시지 전송
            ws_alice.send_json({"content": "Hi Bob!"})

            # Alice가 자신의 메시지 수신
            alice_msg = ws_alice.receive_json()
            assert alice_msg["data"]["content"] == "Hi Bob!"
            assert alice_msg["data"]["sender"] == "Alice"

            # Bob도 메시지 수신
            bob_msg = ws_bob.receive_json()
            assert bob_msg["data"]["content"] == "Hi Bob!"
            assert bob_msg["data"]["sender"] == "Alice"

            # 4. Bob이 응답
            ws_bob.send_json({"content": "Hi Alice!"})

            # Bob이 자신의 메시지 수신
            bob_reply = ws_bob.receive_json()
            assert bob_reply["data"]["content"] == "Hi Alice!"
            assert bob_reply["data"]["sender"] == "Bob"

            # Alice도 응답 수신
            alice_reply = ws_alice.receive_json()
            assert alice_reply["data"]["content"] == "Hi Alice!"
            assert alice_reply["data"]["sender"] == "Bob"


def test_concurrent_room_operations(client):
    """동시 회의방 작업 테스트."""
    # 1. 여러 회의방 생성
    room_ids = []
    for i in range(3):
        response = client.post(
            "/api/rooms",
            json={"name": f"Room {i+1}"}
        )
        assert response.status_code == 201
        room_ids.append(response.json()["id"])

    # 2. 모든 회의방 목록 확인
    list_response = client.get("/api/rooms")
    assert list_response.status_code == 200
    rooms = list_response.json()
    assert len(rooms) == 3

    # 3. 각 회의방에 사용자 연결
    for i, room_id in enumerate(room_ids):
        with client.websocket_connect(f"/ws/{room_id}?username=User{i+1}") as ws:
            join_msg = ws.receive_json()
            assert join_msg["type"] == "system"

            ws.send_json({"content": f"Message in Room {i+1}"})
            msg = ws.receive_json()
            assert msg["data"]["content"] == f"Message in Room {i+1}"

    # 4. 회의방 정리
    for room_id in room_ids:
        delete_response = client.delete(f"/api/rooms/{room_id}")
        assert delete_response.status_code == 204


def test_websocket_disconnect_handling(client):
    """WebSocket 연결 해제 처리 테스트."""
    # 회의방 생성
    create_response = client.post("/api/rooms", json={"name": "Test Room"})
    room_id = create_response.json()["id"]

    # Alice 연결
    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as ws_alice:
        ws_alice.receive_json()  # 입장 메시지

        # Bob 연결
        with client.websocket_connect(f"/ws/{room_id}?username=Bob") as ws_bob:
            # Alice가 Bob 입장 메시지 수신
            ws_alice.receive_json()
            ws_bob.receive_json()  # Bob 입장 메시지

            # Bob 연결 종료 (with 블록 종료)

        # Alice가 Bob 퇴장 메시지 수신
        leave_msg = ws_alice.receive_json()
        assert leave_msg["type"] == "system"
        assert "Bob" in leave_msg["data"]["message"]
        assert "퇴장" in leave_msg["data"]["message"]


def test_room_capacity_and_limits(client):
    """회의방 용량 및 제한 테스트."""
    # 1. 최대 회의방 수 설정 확인
    room_manager = get_room_manager()
    original_max = room_manager.max_rooms
    room_manager.max_rooms = 2

    # 2. 최대 개수만큼 생성
    room1 = client.post("/api/rooms", json={"name": "Room 1"})
    room2 = client.post("/api/rooms", json={"name": "Room 2"})
    assert room1.status_code == 201
    assert room2.status_code == 201

    # 3. 초과 생성 시도
    room3 = client.post("/api/rooms", json={"name": "Room 3"})
    assert room3.status_code == 400

    # 4. 원래 설정 복원
    room_manager.max_rooms = original_max


def test_empty_message_handling(client):
    """빈 메시지 처리 테스트."""
    # 회의방 생성
    create_response = client.post("/api/rooms", json={"name": "Test Room"})
    room_id = create_response.json()["id"]

    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as websocket:
        websocket.receive_json()  # 입장 메시지

        # 빈 메시지 전송
        websocket.send_json({"content": ""})

        # 빈 메시지도 브로드캐스트됨
        message = websocket.receive_json()
        assert message["type"] == "message"
        assert message["data"]["content"] == ""
