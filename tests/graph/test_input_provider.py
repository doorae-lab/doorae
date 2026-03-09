"""InputProvider 추상 클래스 테스트."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestCliInputProvider:
    @pytest.mark.asyncio
    async def test_get_input_returns_user_text(self):
        from doorae.graph.input_provider import CliInputProvider

        provider = CliInputProvider()
        state = {"messages": [], "agendas": [], "current_agenda_idx": 0}

        with patch(
            "doorae.graph.input_provider.asyncio.to_thread",
            new_callable=AsyncMock,
        ) as mock_thread:
            mock_thread.return_value = "테스트 입력"
            result = await provider.get_input(state, "User")

        assert result == "테스트 입력"


class TestQueueInputProvider:
    @pytest.mark.asyncio
    async def test_get_input_returns_queued_message(self):
        from doorae.graph.input_provider import QueueInputProvider

        queue = asyncio.Queue()
        await queue.put("큐 입력")
        provider = QueueInputProvider(input_queue=queue)
        state = {"messages": [], "agendas": [], "current_agenda_idx": 0}

        result = await provider.get_input(state, "User")
        assert result == "큐 입력"

    @pytest.mark.asyncio
    async def test_get_input_none_returns_empty(self):
        from doorae.graph.input_provider import QueueInputProvider

        queue = asyncio.Queue()
        await queue.put(None)
        provider = QueueInputProvider(input_queue=queue)
        state = {"messages": [], "agendas": [], "current_agenda_idx": 0}

        result = await provider.get_input(state, "User")
        assert result == ""

    @pytest.mark.asyncio
    async def test_get_input_uses_queue_getter(self):
        from doorae.graph.input_provider import QueueInputProvider

        alice_queue = asyncio.Queue()
        bob_queue = asyncio.Queue()
        await bob_queue.put("Bob 입력")

        provider = QueueInputProvider(
            queue_getter=lambda username: alice_queue if username == "Alice" else bob_queue
        )
        state = {"messages": [], "agendas": [], "current_agenda_idx": 0}

        result = await provider.get_input(state, "Bob")
        assert result == "Bob 입력"
