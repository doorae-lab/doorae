"""베이스 노드 클래스 및 타입 정의"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, Any
from doorae.graph.state import MeetingState


class NodeType(Enum):
    """노드 타입 분류"""

    AGENT = auto()  # AI 에이전트 노드
    DISPATCH = auto()  # 단일 참가자 디스패치 노드
    UTILITY = auto()  # 상태 처리 노드
    HUMAN = auto()  # 사용자 입력 노드
    ROUTING = auto()  # 라우팅 노드


class BaseNode(ABC):
    """모든 노드의 베이스 클래스

    LangGraph와 호환되는 노드를 만들기 위한 추상 베이스 클래스입니다.
    모든 노드는 이 클래스를 상속받아 execute 메서드를 구현해야 합니다.

    Attributes:
        node_type: 노드의 타입 (AGENT, UTILITY, HUMAN, ROUTING)
        requires_llm: LLM이 필요한 노드인지 여부
        requires_tools: MCP 도구가 필요한 노드인지 여부

    Example:
        >>> class MyNode(BaseNode):
        ...     node_type = NodeType.UTILITY
        ...     async def execute(self, state: MeetingState) -> Dict[str, Any]:
        ...         return {"messages": [...]}
    """

    node_type: NodeType = NodeType.UTILITY
    requires_llm: bool = False
    requires_tools: bool = False

    async def on_enter(self, state: MeetingState) -> None:
        """노드 실행 전 훅

        Args:
            state: 현재 회의 상태
        """
        pass

    async def on_exit(self, state: MeetingState, result: dict) -> dict:
        """노드 실행 후 훅

        Args:
            state: 현재 회의 상태
            result: execute 메서드의 반환값

        Returns:
            처리된 결과 딕셔너리
        """
        return result

    @abstractmethod
    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """핵심 로직 구현

        서브클래스에서 반드시 구현해야 하는 추상 메서드입니다.

        Args:
            state: 현재 회의 상태

        Returns:
            상태 업데이트를 위한 딕셔너리
        """
        pass

    async def __call__(self, state: MeetingState) -> Dict[str, Any]:
        """LangGraph 호환 진입점

        LangGraph는 노드를 callable로 호출하므로,
        이 메서드가 실제 진입점이 됩니다.

        Args:
            state: 현재 회의 상태

        Returns:
            상태 업데이트를 위한 딕셔너리
        """
        await self.on_enter(state)
        result = await self.execute(state)
        return await self.on_exit(state, result)
