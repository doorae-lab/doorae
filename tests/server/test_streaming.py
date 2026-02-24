"""워크플로우 스트리밍 파이프라인 테스트."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from thetable.server.room import Room


@pytest.mark.asyncio
async def test_handle_message_puts_to_queue():
    """handle_message가 사용자 입력 큐에 메시지를 넣는지 테스트."""
    room = Room(room_id="test-room", name="Test Room")

    # 사용자 큐 생성
    queue = room.create_user_queue("Alice")

    # ConnectionManager 모킹
    room.connection_manager.broadcast = AsyncMock()
    room.connection_manager.send_personal_message = AsyncMock()

    # 메시지 전송
    await room.handle_message("Alice", json.dumps({"content": "Hello AI"}))

    # 큐에 메시지가 들어갔는지 확인
    assert not queue.empty()
    queued_content = await queue.get()
    assert queued_content == "Hello AI"

    # 브로드캐스트도 호출되었는지 확인
    room.connection_manager.broadcast.assert_called_once()
    broadcast_data = json.loads(room.connection_manager.broadcast.call_args[0][0])
    assert broadcast_data["type"] == "message"
    assert broadcast_data["data"]["content"] == "Hello AI"
    assert broadcast_data["data"]["sender"] == "Alice"


@pytest.mark.asyncio
async def test_handle_message_without_queue():
    """큐가 없는 사용자의 메시지도 브로드캐스트되는지 테스트."""
    room = Room(room_id="test-room", name="Test Room")
    room.connection_manager.broadcast = AsyncMock()

    # 큐를 만들지 않고 메시지 전송
    await room.handle_message("Bob", json.dumps({"content": "No queue"}))

    # 브로드캐스트는 호출됨
    room.connection_manager.broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_invalid_json():
    """잘못된 JSON 메시지 처리 테스트."""
    room = Room(room_id="test-room", name="Test Room")
    room.connection_manager.send_personal_message = AsyncMock()
    room.connection_manager.broadcast = AsyncMock()

    await room.handle_message("Alice", "not valid json")

    # 에러 메시지가 발신자에게 전송됨
    room.connection_manager.send_personal_message.assert_called_once()
    error_data = json.loads(
        room.connection_manager.send_personal_message.call_args[0][0]
    )
    assert error_data["type"] == "error"

    # 브로드캐스트는 호출되지 않음
    room.connection_manager.broadcast.assert_not_called()


@pytest.mark.asyncio
async def test_start_and_stop_workflow_streaming():
    """워크플로우 스트리밍 시작/중지 테스트."""
    room = Room(room_id="test-room", name="Test Room")
    room.connection_manager.broadcast = AsyncMock()

    # 모킹된 워크플로우 (이벤트 3개를 생산)
    async def mock_astream_events(state, config, version):
        for i in range(3):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": f"token_{i}"},
            }

    mock_workflow = Mock()
    mock_workflow.astream_events = mock_astream_events

    # 스트리밍 시작
    await room.start_workflow_streaming(
        workflow=mock_workflow,
        initial_state={"messages": []},
        config={"recursion_limit": 50},
    )

    # 스트리밍 태스크가 완료될 때까지 대기
    assert room._streaming_task is not None
    await room._streaming_task

    # 3개의 이벤트가 브로드캐스트됨
    assert room.connection_manager.broadcast.call_count == 3

    # 각 이벤트가 올바르게 변환됨
    for i, call in enumerate(room.connection_manager.broadcast.call_args_list):
        event_data = json.loads(call[0][0])
        assert event_data["type"] == "on_chat_model_stream"
        assert "timestamp" in event_data


@pytest.mark.asyncio
async def test_stop_workflow_streaming_cancels_task():
    """워크플로우 중지 시 태스크가 취소되는지 테스트."""
    room = Room(room_id="test-room", name="Test Room")
    room.connection_manager.broadcast = AsyncMock()

    # 무한 스트리밍 워크플로우 모킹
    async def mock_infinite_stream(state, config, version):
        while True:
            yield {"event": "on_chain_start", "data": {}}
            await asyncio.sleep(0.1)

    mock_workflow = Mock()
    mock_workflow.astream_events = mock_infinite_stream

    # 스트리밍 시작
    await room.start_workflow_streaming(
        workflow=mock_workflow,
        initial_state={},
        config={},
    )

    # 잠시 실행되게 둠
    await asyncio.sleep(0.3)

    # 스트리밍 중지
    await room.stop_workflow_streaming()

    assert room._streaming_task is None
    assert room.workflow is None


@pytest.mark.asyncio
async def test_workflow_streaming_error_handling():
    """워크플로우 스트리밍 중 에러 발생 시 처리 테스트."""
    room = Room(room_id="test-room", name="Test Room")
    room.connection_manager.broadcast = AsyncMock()

    # 에러를 발생시키는 워크플로우 모킹
    async def mock_error_stream(state, config, version):
        yield {"event": "on_chain_start", "data": {}}
        raise RuntimeError("LLM 호출 실패")

    mock_workflow = Mock()
    mock_workflow.astream_events = mock_error_stream

    await room.start_workflow_streaming(
        workflow=mock_workflow,
        initial_state={},
        config={},
    )

    await room._streaming_task

    # 첫 번째 이벤트 + 에러 이벤트 = 2번 호출
    assert room.connection_manager.broadcast.call_count == 2

    # 마지막 호출이 에러 이벤트인지 확인
    last_call_data = json.loads(
        room.connection_manager.broadcast.call_args_list[-1][0][0]
    )
    assert last_call_data["type"] == "error"
    assert "워크플로우 오류" in last_call_data["data"]["error"]


@pytest.mark.asyncio
async def test_queue_to_workflow_integration():
    """Queue → 입력 소비 통합 시나리오 테스트."""
    room = Room(room_id="test-room", name="Test Room")

    # 사용자 큐 생성
    queue = room.create_user_queue("Alice")

    # 큐에 입력을 넣고 워크플로우가 읽는 시나리오
    await queue.put("회의를 시작합시다")

    # 워크플로우 입력 제공자가 큐에서 읽는 것을 시뮬레이션
    user_input = await queue.get()
    assert user_input == "회의를 시작합시다"
    assert queue.empty()


def test_room_streaming_task_initial_state():
    """Room 초기 상태에서 스트리밍 태스크가 None인지 테스트."""
    room = Room(room_id="test-room", name="Test Room")

    assert room._streaming_task is None
    assert room.workflow is None
