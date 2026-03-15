"""HumanNode - 사용자 입력 노드 (인터페이스 독립)"""

from typing import Dict, Any, Optional
from langchain_core.messages import HumanMessage
from doorae.core.profile import AgentProfile
from doorae.graph.input_provider import InputProvider
from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.registry import register_node
from doorae.graph.state import MeetingState


class HumanNodeExecutor:
    """Shared human input execution logic."""

    def __init__(self, input_provider: Optional[InputProvider] = None) -> None:
        self.input_provider = input_provider

    async def execute(
        self,
        state: MeetingState,
        profile: AgentProfile,
    ) -> Dict[str, Any]:
        """사용자 입력 대기 및 메시지 추가."""
        if self.input_provider is None:
            raise RuntimeError(
                f"HumanNode({profile.name})에 InputProvider가 설정되지 않았습니다."
            )

        user_input = await self.input_provider.get_input(state, profile.name)

        # 빈 입력 시 스킵
        if not user_input.strip():
            skip_message = HumanMessage(content="(발언 없음)", name=profile.name)
            return {"messages": [skip_message]}

        # 사용자 입력을 메시지로 추가
        user_message = HumanMessage(content=user_input, name=profile.name)
        return {"messages": [user_message]}


@register_node("human", category="human")
class HumanNode(BaseNode):
    """사용자 입력 노드.

    InputProvider를 통해 인터페이스에 독립적으로 입력을 받는다.
    """

    node_type = NodeType.HUMAN

    def __init__(
        self,
        profile: AgentProfile,
        input_provider: Optional[InputProvider] = None,
        **kwargs,
    ):
        """초기화

        Args:
            profile: AgentProfile 객체 (is_human=True)
            input_provider: 사용자 입력 제공자
            **kwargs: 추가 파라미터 (무시됨)
        """
        self.profile = profile
        self.input_provider = input_provider
        self._executor = HumanNodeExecutor(input_provider=input_provider)

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """사용자 입력 대기 및 메시지 추가."""
        return await self._executor.execute(state, self.profile)
