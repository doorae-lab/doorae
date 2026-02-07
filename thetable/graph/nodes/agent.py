"""AgentNode - AI 에이전트 노드"""

import logging
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from thetable.core.profile import AgentProfile
from thetable.agents.base_agent import BaseAgent
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.nodes.registry import register_node
from thetable.graph.state import MeetingState

logger = logging.getLogger(__name__)


@register_node("agent", category="agents")
class AgentNode(BaseNode):
    """AI 에이전트 노드

    LLM 기반 에이전트로 회의에 참여하여 발언합니다.
    BaseAgent를 래핑하여 MCP 도구 사용을 지원합니다.

    Attributes:
        profile: 에이전트 프로필 (이름, 역할, 책임 등)
        agent: BaseAgent 인스턴스
        all_agent_names: 전체 참여자 목록
        all_profiles: 전체 프로필 딕셔너리
    """

    node_type = NodeType.AGENT
    requires_llm = True
    requires_tools = True

    def __init__(
        self,
        profile: AgentProfile,
        model,
        tools: Optional[list] = None,
        all_agent_names: Optional[list[str]] = None,
        all_profiles: Optional[dict] = None,
        mcp_tools: Optional[dict] = None,
        **kwargs,
    ):
        """초기화

        Args:
            profile: 에이전트 프로필
            model: LLM 모델 인스턴스
            tools: MCP tools 리스트 (선택)
            all_agent_names: 전체 참여자 목록
            all_profiles: 전체 프로필 딕셔너리
            mcp_tools: 서버별 MCP tools 딕셔너리 {server_name: [tools]}
            **kwargs: 추가 파라미터 (무시됨)
        """
        self.profile = profile
        self.all_agent_names = all_agent_names or []
        self.all_profiles = all_profiles or {}

        # mcp_tools에서 agent_tools 자동 추출
        if tools is None and mcp_tools and profile.mcp_tools:
            tools = []
            for server_name in profile.mcp_tools:
                if server_name in mcp_tools:
                    tools.extend(mcp_tools[server_name])
            if tools:
                logger.info(
                    f"✅ {profile.name}: {len(tools)}개 MCP 도구 연결 "
                    f"(서버: {', '.join(profile.mcp_tools)})"
                )

        # BaseAgent 생성
        self.agent = BaseAgent(name=profile.name, profile=profile, llm=model)

        # MCP 도구 바인딩
        if tools:
            self.agent.bind_mcp_tools(tools)
            logger.info(f"[{profile.name}] 🔧 MCP 도구 바인딩: {len(tools)}개")
    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """에이전트 발언 생성

        Args:
            state: 현재 회의 상태

        Returns:
            생성된 메시지를 포함한 상태 업데이트 딕셔너리
        """
        messages = state.get("messages", [])
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)
        summary = state.get("summary", "")

        # 대화 기록을 명확한 포맷으로 변환
        formatted_messages = []
        for msg in messages:
            content = getattr(msg, "content", "") or ""
            if not content.strip():
                continue

            name = getattr(msg, "name", None)
            msg_type = type(msg).__name__

            if msg_type == "HumanMessage":
                formatted_messages.append(
                    HumanMessage(content=f"[회의 시작 요청]\n{content}")
                )
            elif msg_type == "AIMessage" and name:
                formatted_messages.append(
                    HumanMessage(content=f"[{name}의 발언]\n{content}")
                )

        # 현재 발언 요청 추가
        formatted_messages.append(
            HumanMessage(
                content=f"이제 {self.profile.name}({self.profile.role})로서 위 대화에 이어 발언해 주세요. 한국어로 간결하게 응답하세요."
            )
        )

        # 프롬프트 구성
        agent_prompt = self._build_agent_prompt()
        agenda_context = self._format_agenda_context(agendas, current_idx)

        # 요약을 시스템 프롬프트에 포함
        if summary:
            enhanced_prompt = f"""{agent_prompt}

## 📝 회의 진행 요약
{summary}

{agenda_context}"""
        else:
            enhanced_prompt = f"{agent_prompt}\n\n{agenda_context}"

        # 시스템 메시지 + 포맷된 대화 기록
        system_msg = SystemMessage(content=enhanced_prompt)
        all_messages = [system_msg] + formatted_messages

        # BaseAgent의 invoke_with_tools 사용
        config = {
            "tags": ["participant", f"speaker:{self.profile.name}"],
            "run_name": self.profile.name,
        }
        response = await self.agent.invoke_with_tools(all_messages, config=config)
        response.name = self.profile.name

        # 빈 응답 처리
        content = getattr(response, "content", "") or ""
        if not content.strip():
            response = AIMessage(
                content=f"({self.profile.name}: 현재 추가 의견이 없습니다.)",
                name=self.profile.name,
            )

        return {"messages": [response]}

    def _build_agent_prompt(self) -> str:
        """프로필에서 에이전트 프롬프트 생성

        Returns:
            에이전트 시스템 프롬프트
        """
        participants_section = ""
        if self.all_agent_names:
            others = [p for p in self.all_agent_names if p != self.profile.name]
            if others:
                # is_human인 참여자에 * 표시
                formatted_participants = []
                for name in others:
                    if name in self.all_profiles:
                        participant_profile = self.all_profiles[name]
                        if participant_profile.is_human:
                            formatted_participants.append(f"{name}*")
                        else:
                            formatted_participants.append(name)
                    else:
                        formatted_participants.append(name)

                participants_section = f"""

## 회의 참여자
다른 참여자: {', '.join(formatted_participants)}
(* 표시는 실제 사용자입니다)

다른 참여자의 의견이 필요하면 자연스럽게 언급하세요.
예: "Designer님의 의견도 듣고 싶습니다"
"""

        # metadata 섹션 생성
        metadata_section = ""
        if self.profile.metadata:
            metadata_lines = ["", "## Context Metadata"]
            metadata_lines.append("다음은 MCP 도구 사용 시 참조할 수 있는 컨텍스트 정보입니다:")
            metadata_lines.append("")

            for key, value in self.profile.metadata.items():
                # 리스트면 쉼표로 구분
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value)
                else:
                    value_str = str(value)
                metadata_lines.append(f"- **{key}**: {value_str}")

            metadata_lines.append("")
            metadata_lines.append("💡 이 정보를 MCP 도구(예: GitHub) 호출 시 적극 활용하세요.")

            metadata_section = "\n".join(metadata_lines)

        return f"""당신은 {self.profile.name}, {self.profile.role}입니다.

## 책임
{chr(10).join(f'- {r}' for r in self.profile.responsibilities)}

## 전문 분야
{chr(10).join(f'- {e}' for e in self.profile.expertise)}
{participants_section}{metadata_section}
간결하고 전문적으로 한국어로 응답하세요."""

    def _format_agenda_context(
        self, agendas: list[dict], current_idx: int
    ) -> str:
        """안건 정보를 프롬프트용으로 포맷팅

        Args:
            agendas: 안건 리스트
            current_idx: 현재 안건 인덱스

        Returns:
            포맷된 안건 컨텍스트 문자열
        """
        if not agendas:
            return ""

        # 상태 이모지 매핑
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "deferred": "⏸️",
        }

        # 전체 안건 목록
        agenda_lines = ["## 📋 회의 안건", ""]
        for i, agenda in enumerate(agendas):
            emoji = status_emoji.get(agenda.get("status", "pending"), "❓")
            title = agenda.get("title", "")

            # 상태 텍스트
            status_text = {
                "pending": "예정",
                "in_progress": "현재 논의 중",
                "completed": "완료",
                "deferred": "보류",
            }.get(agenda.get("status", "pending"), "")

            # 현재 안건 표시
            marker = " ← 현재 안건" if i == current_idx else ""
            agenda_lines.append(f"{i+1}. {emoji} {title} ({status_text}){marker}")

        agenda_lines.append("")

        # 현재 안건 상세 정보
        if 0 <= current_idx < len(agendas):
            current_agenda = agendas[current_idx]
            agenda_lines.extend(
                [
                    "## 🎯 현재 논의 중인 안건",
                    f"**제목**: {current_agenda.get('title', '')}",
                ]
            )

            if current_agenda.get("description"):
                agenda_lines.append(f"**설명**: {current_agenda['description']}")

            if current_agenda.get("required_speakers"):
                speakers = ", ".join(current_agenda["required_speakers"])
                agenda_lines.append(f"**필수 발언자**: {speakers}")

            if current_agenda.get("owner"):
                agenda_lines.append(f"**담당자**: {current_agenda['owner']}")

            if current_agenda.get("decision"):
                agenda_lines.append(f"**결정사항**: {current_agenda['decision']}")

            agenda_lines.append("")
            agenda_lines.append(
                "💡 **지침**: 현재 안건에 집중하여 관련된 의견을 제시하세요."
            )

        return "\n".join(agenda_lines)
