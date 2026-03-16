"""Routes 테스트."""

import doorae.server.routes as routes
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from doorae.server.app import create_app
from doorae.server.room_manager import get_room_manager


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


@pytest.fixture(autouse=True)
def clear_mcp_cache(monkeypatch):
    monkeypatch.setattr("doorae.server.routes._mcp_tools_cache", None, raising=False)


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
        # user_joined 이벤트 수신
        user_joined = websocket.receive_json()
        assert user_joined["type"] == "semantic:user_joined"
        assert user_joined["data"]["username"] == "Alice"

        # 시스템 입장 메시지 수신
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
        # Alice user_joined + 입장 메시지 수신
        ws1.receive_json()  # user_joined
        ws1.receive_json()  # system

        with client.websocket_connect(f"/ws/{room_id}?username=Bob") as ws2:
            # Alice가 Bob user_joined + 입장 메시지 수신
            data = ws1.receive_json()
            assert data["type"] == "semantic:user_joined"
            assert data["data"]["username"] == "Bob"
            data = ws1.receive_json()
            assert data["type"] == "system"
            assert "Bob" in data["data"]["message"]

            # Bob이 participants_list + user_joined + 입장 메시지 수신
            data = ws2.receive_json()
            assert data["type"] == "semantic:participants_list"
            data = ws2.receive_json()
            assert data["type"] == "semantic:user_joined"
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


def test_start_workflow_nonexistent_room(client):
    """존재하지 않는 회의방에 워크플로우 시작 테스트."""
    response = client.post("/api/rooms/nonexistent/start")
    assert response.status_code == 404


def test_start_workflow_no_participants(client):
    """참가자 없는 회의방에 워크플로우 시작 테스트."""
    create_response = client.post("/api/rooms", json={"name": "Empty Room"})
    room_id = create_response.json()["id"]

    response = client.post(f"/api/rooms/{room_id}/start")
    assert response.status_code == 400
    assert "참가자가 없습니다" in response.json()["detail"]


def test_start_workflow_uses_unified_workflow(client, monkeypatch):
    """워크플로우 시작 시 MeetingEngine + 런타임 human 프로필을 사용한다."""
    create_response = client.post("/api/rooms", json={"name": "Team Room"})
    room_id = create_response.json()["id"]

    calls = {}
    mock_registry = object()
    mock_mcp_tools = {"github": [object()]}

    class MockSettings:
        agent_profiles_path = "config/agent_profiles.yaml"
        agendas_path = "config/agendas.yaml"
        recursion_limit = 123
        max_turns = 1000

    class MockEngine:
        def __init__(self, **kwargs):
            calls["engine_kwargs"] = kwargs
            self._setup_state = None

        @property
        def setup_state(self):
            return self._setup_state

        def setup(self):
            calls["setup_called"] = calls.get("setup_called", 0) + 1
            self._setup_state = SimpleNamespace(participant_registry=mock_registry)
            return self._setup_state

    monkeypatch.setattr("doorae.server.routes.get_settings", lambda: MockSettings())
    monkeypatch.setattr("doorae.server.routes.MeetingEngine", MockEngine)
    initialize_mcp_tools = AsyncMock(return_value=mock_mcp_tools)
    monkeypatch.setattr("doorae.server.routes.initialize_mcp_tools", initialize_mcp_tools)

    with client.websocket_connect(f"/ws/{room_id}?username=Alice") as ws:
        ws.receive_json()  # 입장 이벤트

        room = get_room_manager().get_room(room_id)
        room.start_workflow_streaming = AsyncMock()

        response = client.post(f"/api/rooms/{room_id}/start")
        assert response.status_code == 200

        engine_kwargs = calls["engine_kwargs"]
        assert engine_kwargs["profiles_path"] == "config/agent_profiles.yaml"
        assert engine_kwargs["initial_message"] == "회의를 시작합니다"
        assert "input_provider" in engine_kwargs
        assert engine_kwargs["mcp_tools"] == mock_mcp_tools
        assert "profiles_override" in engine_kwargs
        assert "Alice" in engine_kwargs["profiles_override"]
        assert engine_kwargs["profiles_override"]["Alice"].is_human is True
        assert calls["setup_called"] == 1
        assert room.participant_registry is mock_registry
        initialize_mcp_tools.assert_awaited_once()

        room.start_workflow_streaming.assert_awaited_once()
        assert isinstance(room.start_workflow_streaming.await_args.kwargs["engine"], MockEngine)


@pytest.mark.asyncio
async def test_get_mcp_tools_caches_initialized_tools(monkeypatch):
    mock_mcp_tools = {"github": [object()]}
    initialize_mcp_tools = AsyncMock(return_value=mock_mcp_tools)
    monkeypatch.setattr("doorae.server.routes.initialize_mcp_tools", initialize_mcp_tools)

    first = await routes._get_mcp_tools()
    second = await routes._get_mcp_tools()

    assert first is mock_mcp_tools
    assert second is mock_mcp_tools
    initialize_mcp_tools.assert_awaited_once()
