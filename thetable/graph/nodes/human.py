"""HumanNode - 사용자 입력 노드"""

import asyncio
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from prompt_toolkit import prompt as pt_prompt
from thetable.core.profile import AgentProfile
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.nodes.registry import register_node
from thetable.graph.state import MeetingState


@register_node("human", category="human")
class HumanNode(BaseNode):
    """사용자 입력 노드

    터미널에서 사용자 입력을 받아 회의에 참여합니다.
    prompt_toolkit을 사용하여 한글 UTF-8 인코딩 문제를 해결합니다.

    Attributes:
        profile: 사용자 프로필 (is_human=True)
    """

    node_type = NodeType.HUMAN

    def __init__(self, profile: AgentProfile, **kwargs):
        """초기화

        Args:
            profile: AgentProfile 객체 (is_human=True)
            **kwargs: 추가 파라미터 (무시됨)
        """
        self.profile = profile

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """사용자 입력 대기 및 메시지 추가

        Args:
            state: 현재 회의 상태

        Returns:
            사용자 메시지를 포함한 상태 업데이트 딕셔너리
        """
        messages = state.get("messages", [])
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)

        # 현재 안건 정보 표시
        print(f"\n{'='*60}", flush=True)
        print(f"[{self.profile.name}님 차례입니다]", flush=True)

        if current_idx < len(agendas):
            current_agenda = agendas[current_idx]
            print(
                f"\n📋 현재 안건: {current_agenda.get('title', 'N/A')}", flush=True
            )
            print(f"   설명: {current_agenda.get('description', 'N/A')}", flush=True)

        # 최근 발언 표시 (최대 3개)
        if messages:
            print(f"\n💬 최근 발언:", flush=True)
            recent_messages = messages[-3:]
            for msg in recent_messages:
                speaker = getattr(msg, "name", "Unknown")
                content = getattr(msg, "content", "")
                # 길면 첫 100자만 표시
                display_content = (
                    content[:100] + "..." if len(content) > 100 else content
                )
                print(f"   [{speaker}] {display_content}", flush=True)

        print(f"\n{'='*60}", flush=True)
        print(f"💡 의견을 입력하세요 (빈 입력 시 스킵):", flush=True)

        # prompt_toolkit을 사용하여 한글 UTF-8 인코딩 문제 해결
        # asyncio.to_thread로 감싸서 비동기 처리
        user_input = await asyncio.to_thread(pt_prompt, "> ")

        # 빈 입력 시 스킵
        if not user_input.strip():
            print(f"[{self.profile.name}님이 스킵했습니다]\n", flush=True)
            # 빈 메시지 추가 (스킵 표시용)
            skip_message = HumanMessage(
                content="(발언 없음)", name=self.profile.name
            )
            return {"messages": [skip_message]}

        # 사용자 입력을 메시지로 추가
        user_message = HumanMessage(content=user_input, name=self.profile.name)

        return {"messages": [user_message]}
