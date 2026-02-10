"""UserInputNode - WebSocket 사용자 입력 노드."""

import asyncio
from typing import Any, Dict
from langchain_core.messages import HumanMessage
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.state import MeetingState


class UserInputNode(BaseNode):
    """WebSocket 기반 사용자 입력 노드.

    Room에서 관리하는 입력 큐를 통해 사용자 입력을 받습니다.

    Attributes:
        input_queue: 사용자 입력을 받는 asyncio.Queue
        username: 현재 입력을 기다리는 사용자 이름
    """

    node_type = NodeType.HUMAN

    def __init__(self, input_queue: asyncio.Queue, username: str):
        """초기화.

        Args:
            input_queue: 사용자 입력을 받는 asyncio.Queue
            username: 사용자 이름
        """
        self.input_queue = input_queue
        self.username = username

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """사용자 입력 대기 및 메시지 추가.

        Args:
            state: 현재 회의 상태

        Returns:
            사용자 메시지를 포함한 상태 업데이트 딕셔너리
        """
        # 입력 큐에서 사용자 입력 대기
        user_input = await self.input_queue.get()

        # 빈 입력 처리
        if not user_input or not user_input.strip():
            skip_message = HumanMessage(
                content="(발언 없음)",
                name=self.username
            )
            return {"messages": [skip_message]}

        # 사용자 입력을 메시지로 추가
        user_message = HumanMessage(
            content=user_input,
            name=self.username
        )

        return {"messages": [user_message]}
