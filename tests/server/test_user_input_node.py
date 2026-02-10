"""UserInputNode 테스트."""

import asyncio
import pytest
from thetable.server.user_input_node import UserInputNode
from thetable.graph.state import MeetingState
from thetable.graph.nodes.base import NodeType


@pytest.mark.asyncio
async def test_user_input_node_type():
    """UserInputNode 타입 테스트."""
    queue = asyncio.Queue()
    node = UserInputNode(input_queue=queue, username="Alice")
    assert node.node_type == NodeType.HUMAN


@pytest.mark.asyncio
async def test_user_input_node_with_input():
    """사용자 입력이 있는 경우 테스트."""
    queue = asyncio.Queue()
    await queue.put("Hello, world!")

    node = UserInputNode(input_queue=queue, username="Alice")
    state = MeetingState(messages=[], pending_speakers=[])

    result = await node.execute(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert message.content == "Hello, world!"
    assert message.name == "Alice"


@pytest.mark.asyncio
async def test_user_input_node_empty_input():
    """빈 입력 테스트."""
    queue = asyncio.Queue()
    await queue.put("")

    node = UserInputNode(input_queue=queue, username="Alice")
    state = MeetingState(messages=[], pending_speakers=[])

    result = await node.execute(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert message.content == "(발언 없음)"
    assert message.name == "Alice"


@pytest.mark.asyncio
async def test_user_input_node_whitespace_input():
    """공백 입력 테스트."""
    queue = asyncio.Queue()
    await queue.put("   ")

    node = UserInputNode(input_queue=queue, username="Bob")
    state = MeetingState(messages=[], pending_speakers=[])

    result = await node.execute(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert message.content == "(발언 없음)"
    assert message.name == "Bob"
