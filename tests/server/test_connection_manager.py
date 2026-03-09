"""ConnectionManager 테스트."""

import pytest
from unittest.mock import Mock, AsyncMock
from doorae.server.connection_manager import ConnectionManager


def test_connection_manager_init():
    """ConnectionManager 초기화 테스트."""
    manager = ConnectionManager()
    assert manager.connections == {}
    assert manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_connect():
    """WebSocket 연결 테스트."""
    manager = ConnectionManager()
    websocket = Mock()
    websocket.accept = AsyncMock()

    await manager.connect("Alice", websocket)

    assert "Alice" in manager.connections
    assert manager.get_connection_count() == 1
    websocket.accept.assert_called_once()


def test_disconnect():
    """WebSocket 연결 해제 테스트."""
    manager = ConnectionManager()
    websocket = Mock()
    manager.connections["Alice"] = websocket

    manager.disconnect("Alice")

    assert "Alice" not in manager.connections
    assert manager.get_connection_count() == 0


def test_disconnect_nonexistent():
    """존재하지 않는 연결 해제 테스트."""
    manager = ConnectionManager()
    manager.disconnect("Alice")  # 에러 없이 실행되어야 함
    assert manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_send_personal_message():
    """개인 메시지 전송 테스트."""
    manager = ConnectionManager()
    websocket = Mock()
    websocket.send_text = AsyncMock()
    manager.connections["Alice"] = websocket

    await manager.send_personal_message("Hello Alice", "Alice")

    websocket.send_text.assert_called_once_with("Hello Alice")


@pytest.mark.asyncio
async def test_send_personal_message_nonexistent():
    """존재하지 않는 사용자에게 메시지 전송 테스트."""
    manager = ConnectionManager()
    # 에러 없이 실행되어야 함
    await manager.send_personal_message("Hello", "Nobody")


@pytest.mark.asyncio
async def test_broadcast():
    """브로드캐스트 테스트."""
    manager = ConnectionManager()

    websocket1 = Mock()
    websocket1.send_text = AsyncMock()
    websocket2 = Mock()
    websocket2.send_text = AsyncMock()

    manager.connections["Alice"] = websocket1
    manager.connections["Bob"] = websocket2

    await manager.broadcast("Hello everyone")

    websocket1.send_text.assert_called_once_with("Hello everyone")
    websocket2.send_text.assert_called_once_with("Hello everyone")


