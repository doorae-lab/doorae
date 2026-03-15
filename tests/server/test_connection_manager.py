"""ConnectionManager 테스트."""

import pytest
from unittest.mock import Mock, AsyncMock
from doorae.server.connection_manager import ConnectionInfo, ConnectionManager


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
    assert manager.connections["Alice"].websocket is websocket
    assert manager.connections["Alice"].raw_events is True
    assert manager.get_connection_count() == 1
    websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_can_disable_raw_events():
    manager = ConnectionManager()
    websocket = Mock()
    websocket.accept = AsyncMock()

    await manager.connect("Alice", websocket, raw_events=False)

    assert manager.connections["Alice"].raw_events is False


def test_disconnect():
    """WebSocket 연결 해제 테스트."""
    manager = ConnectionManager()
    websocket = Mock()
    manager.connections["Alice"] = ConnectionInfo(websocket=websocket)

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
    manager.connections["Alice"] = ConnectionInfo(websocket=websocket)

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

    manager.connections["Alice"] = ConnectionInfo(websocket=websocket1)
    manager.connections["Bob"] = ConnectionInfo(websocket=websocket2)

    await manager.broadcast("Hello everyone")

    websocket1.send_text.assert_called_once_with("Hello everyone")
    websocket2.send_text.assert_called_once_with("Hello everyone")


@pytest.mark.asyncio
async def test_broadcast_raw_channel_filters_opted_out_connections():
    manager = ConnectionManager()

    websocket1 = Mock()
    websocket1.send_text = AsyncMock()
    websocket2 = Mock()
    websocket2.send_text = AsyncMock()

    manager.connections["Alice"] = ConnectionInfo(websocket=websocket1, raw_events=True)
    manager.connections["Bob"] = ConnectionInfo(websocket=websocket2, raw_events=False)

    await manager.broadcast("raw payload", channel="raw")

    websocket1.send_text.assert_called_once_with("raw payload")
    websocket2.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_handles_disconnect_during_iteration():
    """순회 중 연결이 제거되어도 브로드캐스트가 실패하지 않아야 한다."""
    manager = ConnectionManager()

    websocket1 = Mock()
    websocket2 = Mock()

    async def disconnect_bob(_: str):
        manager.disconnect("Bob")

    websocket1.send_text = AsyncMock(side_effect=disconnect_bob)
    websocket2.send_text = AsyncMock()

    manager.connections["Alice"] = ConnectionInfo(websocket=websocket1)
    manager.connections["Bob"] = ConnectionInfo(websocket=websocket2)

    await manager.broadcast("Hello everyone")

    websocket1.send_text.assert_called_once_with("Hello everyone")
    websocket2.send_text.assert_not_called()
    assert list(manager.connections) == ["Alice"]
    assert manager.connections["Alice"].websocket is websocket1


@pytest.mark.asyncio
async def test_broadcast_keeps_reconnected_socket_on_failure():
    """전송 실패 중 재연결된 새 소켓은 정리 대상이 아니어야 한다."""
    manager = ConnectionManager()

    old_websocket = Mock()
    new_websocket = Mock()
    new_websocket.send_text = AsyncMock()

    async def fail_after_reconnect(_: str):
        manager.connections["Alice"] = ConnectionInfo(websocket=new_websocket)
        raise RuntimeError("socket closed")

    old_websocket.send_text = AsyncMock(side_effect=fail_after_reconnect)
    manager.connections["Alice"] = ConnectionInfo(websocket=old_websocket)

    await manager.broadcast("Hello everyone")

    assert manager.connections["Alice"].websocket is new_websocket
    new_websocket.send_text.assert_not_called()


@pytest.mark.asyncio
async def test_send_personal_message_keeps_reconnected_socket_on_failure():
    """개인 전송 실패 중 재연결된 새 소켓은 제거하지 않아야 한다."""
    manager = ConnectionManager()

    old_websocket = Mock()
    new_websocket = Mock()

    async def fail_after_reconnect(_: str):
        manager.connections["Alice"] = ConnectionInfo(websocket=new_websocket)
        raise RuntimeError("socket closed")

    old_websocket.send_text = AsyncMock(side_effect=fail_after_reconnect)
    manager.connections["Alice"] = ConnectionInfo(websocket=old_websocket)

    await manager.send_personal_message("Hello Alice", "Alice")

    assert manager.connections["Alice"].websocket is new_websocket
