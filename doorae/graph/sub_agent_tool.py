"""Sub-agent tool factory."""

from __future__ import annotations

import re
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from doorae.agents.base_agent import BaseAgent
from doorae.core.date_context import format_today_context
from doorae.core.profile import AgentProfile


class SubAgentInput(BaseModel):
    """하위 에이전트 Tool 입력 스키마."""

    question: str = Field(description="하위 에이전트에게 전달할 질문/요청")


def _normalize_tool_name(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", "_", name.lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "sub_agent"


def _build_tool_description(sub_profile: AgentProfile, parent_name: str) -> str:
    responsibilities = ", ".join(sub_profile.responsibilities[:3]) or "역할 기반 지원"
    expertise = ", ".join(sub_profile.expertise[:3]) or "일반"
    return (
        f"{sub_profile.name}({sub_profile.role})에게 의견을 요청합니다. "
        f"상위 에이전트: {parent_name}. "
        f"책임: {responsibilities}. "
        f"전문분야: {expertise}."
    )


def create_sub_agent_tool(
    sub_profile: AgentProfile,
    model,
    parent_name: str,
    mcp_tools: Optional[dict[str, list]] = None,
) -> StructuredTool:
    """하위 에이전트를 Tool로 래핑하여 반환."""
    sub_agent = BaseAgent(name=sub_profile.name, profile=sub_profile, llm=model)

    available_mcp_tools: list = []
    if mcp_tools and sub_profile.mcp_tools:
        for server_name in sub_profile.mcp_tools:
            available_mcp_tools.extend(mcp_tools.get(server_name, []))
    if available_mcp_tools:
        sub_agent.bind_mcp_tools(available_mcp_tools)

    async def ask_sub_agent(question: str) -> str:
        messages = [
            SystemMessage(
                content=(
                    f"당신은 {sub_profile.name}({sub_profile.role})입니다. "
                    f"상위 에이전트 {parent_name}의 위임을 받아 답변합니다. "
                    f"{format_today_context()} "
                    "핵심만 간결하게 한국어로 답하세요."
                )
            ),
            HumanMessage(content=question),
        ]
        response = await sub_agent.invoke_with_tools(
            messages,
            config={
                "tags": ["participant", f"speaker:{sub_profile.name}", f"delegated_by:{parent_name}"],
                "run_name": sub_profile.name,
            },
        )
        content = getattr(response, "content", "") or ""
        return content.strip() or f"{sub_profile.name}의 응답이 비어 있습니다."

    tool_name = f"ask_{_normalize_tool_name(sub_profile.name)}"
    return StructuredTool.from_function(
        coroutine=ask_sub_agent,
        name=tool_name,
        description=_build_tool_description(sub_profile, parent_name),
        args_schema=SubAgentInput,
    )
