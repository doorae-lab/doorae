"""AgentNode - AI 에이전트 노드."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from doorae.agents.base_agent import BaseAgent
from doorae.core.date_context import format_today_context
from doorae.core.profile import AgentProfile
from doorae.graph.agenda_tools import (
    create_approve_tool,
    create_propose_tool,
    create_reject_tool,
)
from doorae.graph.constants import (
    HOST_END_MEETING_COMMAND,
    HOST_ROLE_NAME,
    STATUS_EMOJI,
    STATUS_TEXT,
)
from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.registry import register_node
from doorae.graph.state import MeetingState, ParticipantStatus
from doorae.graph.sub_agent_tool import create_sub_agent_tool


class AgentNodeExecutor:
    """Reusable execution logic for AI participant turns."""

    def __init__(
        self,
        profile: AgentProfile,
        model=None,
        tools: Optional[list] = None,
        mcp_tools: Optional[dict] = None,
        settings=None,
    ) -> None:
        self.profile = profile
        self.sub_agent_tools: list = []
        self._mcp_tools = mcp_tools or {}

        if model is None:
            from doorae.config import create_agent_llm, get_settings

            model = create_agent_llm(
                profile=profile,
                settings=settings or get_settings(),
                streaming=True,
            )

        if tools is None and self._mcp_tools and profile.mcp_tools:
            tools = []
            for server_name in profile.mcp_tools:
                if server_name in self._mcp_tools:
                    tools.extend(self._mcp_tools[server_name])
            if tools:
                logger.info(
                    f"✅ {profile.name}: {len(tools)}개 MCP 도구 연결 "
                    f"(서버: {', '.join(profile.mcp_tools)})"
                )

        self.agent = BaseAgent(name=profile.name, profile=profile, llm=model)

        if tools:
            self.agent.bind_mcp_tools(tools)
            logger.info(f"[{profile.name}] 🔧 MCP 도구 바인딩: {len(tools)}개")

        if profile.is_supervisor():
            for sub_profile in profile.agents or []:
                sub_tool = create_sub_agent_tool(
                    sub_profile=sub_profile,
                    model=model,
                    parent_name=profile.name,
                    mcp_tools=self._mcp_tools,
                )
                self.sub_agent_tools.append(sub_tool)
            if self.sub_agent_tools:
                logger.info(
                    f"[{profile.name}] 👥 하위 에이전트 도구 바인딩: "
                    f"{len(self.sub_agent_tools)}개"
                )

    async def execute(
        self,
        state: MeetingState,
        *,
        all_agent_names: Optional[list[str]] = None,
        all_profiles: Optional[Mapping[str, AgentProfile]] = None,
    ) -> Dict[str, Any]:
        """에이전트 발언 생성."""
        messages = state.get("messages", [])
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)
        summary = state.get("summary", "")
        pending_proposals: List[dict] = list(state.get("pending_proposals", []))
        participant_statuses: Dict[str, str] = dict(state.get("participant_statuses", {}))

        formatted_messages = []
        for msg in messages:
            content = getattr(msg, "content", "") or ""
            if not content.strip():
                continue

            name = getattr(msg, "name", None)
            msg_type = type(msg).__name__

            if msg_type == "HumanMessage":
                formatted_messages.append(HumanMessage(content=f"[회의 시작 요청]\n{content}"))
            elif msg_type == "AIMessage" and name:
                formatted_messages.append(HumanMessage(content=f"[{name}의 발언]\n{content}"))

        formatted_messages.append(
            HumanMessage(
                content=(
                    f"이제 {self.profile.name}({self.profile.role})로서 위 대화에 이어 "
                    "발언해 주세요. 한국어로 간결하게 응답하세요."
                )
            )
        )

        agent_prompt = self._build_agent_prompt(
            all_agent_names=all_agent_names,
            all_profiles=all_profiles,
        )
        agenda_context = self._format_agenda_context(agendas, current_idx)

        if summary:
            enhanced_prompt = f"""{agent_prompt}

## 📝 회의 진행 요약
{summary}

{agenda_context}"""
        else:
            enhanced_prompt = f"{agent_prompt}\n\n{agenda_context}"

        if self.profile.name == HOST_ROLE_NAME and pending_proposals:
            enhanced_prompt += "\n\n" + self._format_proposals_context(pending_proposals)

        system_msg = SystemMessage(content=enhanced_prompt)
        all_messages = [system_msg] + formatted_messages

        agenda_actions: list = []
        agenda_tools = [create_propose_tool(agenda_actions, self.profile.name)]
        if self.profile.name == HOST_ROLE_NAME and pending_proposals:
            agenda_tools.append(create_approve_tool(agenda_actions, pending_proposals))
            agenda_tools.append(create_reject_tool(agenda_actions, pending_proposals))

        all_tools = agenda_tools + self.sub_agent_tools

        config = {
            "tags": ["participant", f"speaker:{self.profile.name}"],
            "run_name": self.profile.name,
        }
        participant_statuses[self.profile.name] = ParticipantStatus.speaking.value
        if all_tools or getattr(self.agent, "_mcp_tools", []):
            participant_statuses[self.profile.name] = ParticipantStatus.tool_calling.value

        response = await self.agent.invoke_with_tools(
            all_messages,
            config=config,
            extra_tools=all_tools,
        )
        response.name = self.profile.name

        content = getattr(response, "content", "") or ""
        if not content.strip():
            response = AIMessage(
                content=f"({self.profile.name}: 현재 추가 의견이 없습니다.)",
                name=self.profile.name,
            )

        participant_statuses[self.profile.name] = ParticipantStatus.idle.value
        result: Dict[str, Any] = {
            "messages": [response],
            "participant_statuses": participant_statuses,
        }

        if agenda_actions:
            result.update(
                self._apply_agenda_actions(
                    agenda_actions,
                    pending_proposals,
                    agendas,
                )
            )

        return result

    def _build_agent_prompt(
        self,
        *,
        all_agent_names: Optional[list[str]] = None,
        all_profiles: Optional[Mapping[str, AgentProfile]] = None,
    ) -> str:
        """프로필에서 에이전트 프롬프트 생성."""
        participants_section = ""
        names = all_agent_names or []
        profiles = all_profiles or {}
        if names:
            others = [participant for participant in names if participant != self.profile.name]
            if others:
                formatted_participants = []
                for name in others:
                    participant_profile = profiles.get(name)
                    if participant_profile is not None and participant_profile.is_human:
                        formatted_participants.append(f"{name}*")
                    else:
                        formatted_participants.append(name)

                participants_section = f"""

## 회의 참여자
다른 참여자: {', '.join(formatted_participants)}
(* 표시는 실제 사용자입니다)

다른 참여자의 응답이 필요하면 반드시 @이름 형식으로 호출하세요.
예: "@PM 의견 부탁드립니다"
여러 명을 호출할 때는 "@PM @TechLead 검토 부탁드립니다"처럼 작성하세요.
조사나 존칭은 붙여도 되지만, 반드시 @이름 prefix를 포함해야 합니다.
                """

        metadata_section = ""
        if self.profile.metadata:
            metadata_lines = ["", "## Context Metadata"]
            metadata_lines.append("다음은 MCP 도구 사용 시 참조할 수 있는 컨텍스트 정보입니다:")
            metadata_lines.append("")

            for key, value in self.profile.metadata.items():
                value_str = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
                metadata_lines.append(f"- **{key}**: {value_str}")

            metadata_lines.append("")
            metadata_lines.append("💡 이 정보를 MCP 도구(예: GitHub) 호출 시 적극 활용하세요.")
            metadata_section = "\n".join(metadata_lines)

        host_end_protocol_section = ""
        if self.profile.name == HOST_ROLE_NAME:
            host_end_protocol_section = f"""

## 회의 종료 프로토콜
회의를 종료할 때만 마지막 줄에 아래 종료 커맨드를 정확히 한 줄로 출력하세요.
마지막 비어있지 않은 줄은 반드시 이 토큰과 정확히 일치해야 합니다.
평소 발언이나 안건 전환 중에는 이 토큰을 절대 출력하지 마세요.

예시:
오늘 회의는 여기까지 정리하겠습니다. 후속 작업은 문서로 공유드리겠습니다.
{HOST_END_MEETING_COMMAND}
            """

        role_defaults_section = ""
        try:
            import os
            import yaml as _yaml

            defaults_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "config",
                "role_defaults.yaml",
            )
            if os.path.exists(defaults_path):
                with open(defaults_path, "r", encoding="utf-8") as file:
                    defaults_config = _yaml.safe_load(file)
                defaults = defaults_config.get("role_defaults", {})
                rules = list(defaults.get("_all", []))
                rules.extend(defaults.get(self.profile.role, []))
                if rules:
                    role_defaults_section = "\n\n## 역할 행동 규칙\n" + "\n".join(
                        f"- {rule}" for rule in rules
                    )
        except Exception:
            pass

        return f"""당신은 {self.profile.name}, {self.profile.role}입니다.

{format_today_context()}

## 책임
{chr(10).join(f'- {responsibility}' for responsibility in self.profile.responsibilities)}

## 전문 분야
{chr(10).join(f'- {expertise}' for expertise in self.profile.expertise)}
{participants_section}{metadata_section}{host_end_protocol_section}{role_defaults_section}
간결하고 전문적으로 한국어로 응답하세요."""

    def _format_agenda_context(self, agendas: list[dict], current_idx: int) -> str:
        """안건 정보를 프롬프트용으로 포맷팅."""
        if not agendas:
            return ""

        agenda_lines = ["## 📋 회의 안건", ""]
        for index, agenda in enumerate(agendas):
            emoji = STATUS_EMOJI.get(agenda.get("status", "pending"), "❓")
            title = agenda.get("title", "")
            status_str = STATUS_TEXT.get(agenda.get("status", "pending"), "")
            marker = " ← 현재 안건" if index == current_idx else ""
            agenda_lines.append(f"{index+1}. {emoji} {title} ({status_str}){marker}")

        agenda_lines.append("")

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

            scope_notes = []
            if current_idx > 0:
                prev_agenda = agendas[current_idx - 1]
                prev_title = prev_agenda.get("title", "")
                if prev_agenda.get("status") == "completed":
                    scope_notes.append(
                        f"'{prev_title}'에서 이미 논의된 내용은 반복하지 마세요. 새로운 관점만 추가하세요."
                    )

            if current_idx < len(agendas) - 1:
                next_agenda = agendas[current_idx + 1]
                next_title = next_agenda.get("title", "")
                scope_notes.append(
                    f"'{next_title}'에서 다룰 내용은 이 안건에서 논의하지 마세요."
                )

            title_lower = current_agenda.get("title", "").lower()
            if "리뷰" in title_lower or "현황" in title_lower:
                scope_notes.append(
                    "리뷰/현황 안건: MCP 도구로 데이터를 조회한 후 수치 기반으로 논의하세요. "
                    "이슈/PR 전수 나열은 피하고 핵심 지표 3-5개로 요약하세요."
                )
            if "계획" in title_lower or "플래닝" in title_lower:
                scope_notes.append(
                    "계획 안건: 구체적인 일정, 담당자, 완료 기준을 포함하세요. "
                    "추상적인 방향만 제시하지 마세요."
                )
            if "로드맵" in title_lower or "우선순위" in title_lower:
                scope_notes.append(
                    "로드맵 안건: '무엇을 할 것인가'(목표, 우선순위)에 집중하세요. "
                    "구체적 일정/데드라인은 별도 계획 안건에서 다룹니다."
                )

            agenda_lines.append("")
            if scope_notes:
                agenda_lines.append("## 🎯 현재 안건 지침")
                for note in scope_notes:
                    agenda_lines.append(f"- {note}")
            else:
                agenda_lines.append("💡 **지침**: 현재 안건에 집중하여 관련된 의견을 제시하세요.")

        return "\n".join(agenda_lines)

    def _format_proposals_context(self, proposals: List[dict]) -> str:
        """Host 프롬프트용 대기 중인 안건 후보 목록 포맷팅."""
        lines = ["## ⏳ 대기 중인 안건 후보 (Host 승인 필요)", ""]
        for index, proposal in enumerate(proposals):
            title = proposal.get("title", "")
            description = proposal.get("description", "")
            proposed_by = proposal.get("proposed_by", "")
            desc_str = f" — {description}" if description else ""
            lines.append(f"{index}. [{proposed_by}] {title}{desc_str}")
        lines.append("")
        lines.append("💡 approve_agenda(index) 또는 reject_agenda(index, reason)로 처리하세요.")
        return "\n".join(lines)

    def _apply_agenda_actions(
        self,
        actions: List[dict],
        pending_proposals: List[dict],
        agendas: List[dict],
    ) -> Dict[str, Any]:
        """안건 액션을 state update dict로 변환."""
        new_proposals = list(pending_proposals)
        new_agendas = list(agendas)
        remove_indices = set()

        for action in actions:
            act = action.get("action")
            if act == "propose":
                new_proposals.append(action["data"])
                logger.info(
                    f"[{self.profile.name}] 📋 안건 후보 등록: "
                    f"'{action['data'].get('title', '')}'"
                )
            elif act == "approve":
                index = action.get("index")
                if (
                    index is not None
                    and 0 <= index < len(pending_proposals)
                    and index not in remove_indices
                ):
                    remove_indices.add(index)
                    new_agendas.append(action["data"])
                    logger.info(
                        f"[{self.profile.name}] ✅ 안건 승인: "
                        f"'{action['data'].get('title', '')}'"
                    )
            elif act == "reject":
                index = action.get("index")
                if index is not None and 0 <= index < len(pending_proposals):
                    remove_indices.add(index)
                    logger.info(f"[{self.profile.name}] ❌ 안건 거절 (idx={index})")

        for index in sorted(remove_indices, reverse=True):
            if index < len(new_proposals):
                new_proposals.pop(index)

        return {"pending_proposals": new_proposals, "agendas": new_agendas}


@register_node("agent", category="agents")
class AgentNode(BaseNode):
    """AI 에이전트 노드."""

    node_type = NodeType.AGENT
    requires_llm = True
    requires_tools = True

    def __init__(
        self,
        profile: AgentProfile,
        model=None,
        tools: Optional[list] = None,
        all_agent_names: Optional[list[str]] = None,
        all_profiles: Optional[dict] = None,
        mcp_tools: Optional[dict] = None,
        settings=None,
        **kwargs,
    ):
        self.profile = profile
        self.all_agent_names = all_agent_names or []
        self.all_profiles = all_profiles or {}
        self._executor = AgentNodeExecutor(
            profile=profile,
            model=model,
            tools=tools,
            mcp_tools=mcp_tools,
            settings=settings,
        )
        self.agent = self._executor.agent
        self.sub_agent_tools = self._executor.sub_agent_tools

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        return await self._executor.execute(
            state,
            all_agent_names=self.all_agent_names,
            all_profiles=self.all_profiles,
        )

    def _build_agent_prompt(self) -> str:
        return self._executor._build_agent_prompt(
            all_agent_names=self.all_agent_names,
            all_profiles=self.all_profiles,
        )

    def _apply_agenda_actions(
        self,
        actions: List[dict],
        pending_proposals: List[dict],
        agendas: List[dict],
    ) -> Dict[str, Any]:
        return self._executor._apply_agenda_actions(actions, pending_proposals, agendas)
