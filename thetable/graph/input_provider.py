"""사용자 입력 제공자 추상화."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable

from thetable.graph.state import MeetingState


class InputProvider(ABC):
    """사용자 입력을 제공하는 추상 인터페이스."""

    @abstractmethod
    async def get_input(self, state: MeetingState, username: str) -> str:
        """사용자 입력을 비동기로 받아 반환한다."""


class CliInputProvider(InputProvider):
    """터미널(stdin) 기반 입력 제공자."""

    async def get_input(self, state: MeetingState, username: str) -> str:
        from prompt_toolkit import prompt as pt_prompt

        messages = state.get("messages", [])
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)

        print(f"\n{'='*60}", flush=True)
        print(f"[{username}님 차례입니다]", flush=True)

        if current_idx < len(agendas):
            current_agenda = agendas[current_idx]
            print(f"\n📋 현재 안건: {current_agenda.get('title', 'N/A')}", flush=True)
            print(f"   설명: {current_agenda.get('description', 'N/A')}", flush=True)

        if messages:
            print("\n💬 최근 발언:", flush=True)
            for msg in messages[-3:]:
                speaker = getattr(msg, "name", "Unknown")
                content = getattr(msg, "content", "")
                display = content[:100] + "..." if len(content) > 100 else content
                print(f"   [{speaker}] {display}", flush=True)

        print(f"\n{'='*60}", flush=True)
        print("💡 의견을 입력하세요 (빈 입력 시 스킵):", flush=True)

        return await asyncio.to_thread(pt_prompt, "> ")


class QueueInputProvider(InputProvider):
    """asyncio.Queue 기반 입력 제공자."""

    def __init__(
        self,
        input_queue: asyncio.Queue | None = None,
        queue_getter: Callable[[str], asyncio.Queue | None] | None = None,
    ):
        if queue_getter is None and input_queue is None:
            raise ValueError("input_queue 또는 queue_getter 중 하나는 필요합니다.")

        self._queue_getter = queue_getter or (lambda _username: input_queue)

    async def get_input(self, state: MeetingState, username: str) -> str:
        queue = self._queue_getter(username)
        if queue is None:
            return ""

        user_input = await queue.get()
        return user_input if user_input is not None else ""
