"""Prompt templates and builders for supervisors"""

from thetable.core.profile import AgentProfile


def build_handoff_tools_section(child_names: list[str]) -> str:
    """핸드오프 도구 문서 섹션 생성

    Args:
        child_names: 하위 에이전트 이름 목록

    Returns:
        핸드오프 도구 설명 문자열

    Note:
        langgraph-supervisor는 도구 이름을 생성할 때 에이전트 이름을 소문자로 변환합니다.
        따라서 'TechLead' → 'transfer_to_techlead'로 변환됩니다.
    """
    if not child_names:
        return ""

    tool_descriptions = []
    for name in child_names:
        # langgraph-supervisor의 _normalize_agent_name()이 소문자로 변환하므로
        # 프롬프트에서도 소문자로 안내
        normalized_name = name.lower()
        tool_descriptions.append(f"- transfer_to_{normalized_name}: {name}에게 작업 위임")

    return "\n".join(tool_descriptions)


def build_supervisor_prompt(
    profile: AgentProfile,
    child_names: list[str],
    template: str | None = None
) -> str:
    """supervisor 프롬프트 생성 (Host 및 중첩 supervisor 모두 지원)

    Args:
        profile: 에이전트 프로필
        child_names: 하위 에이전트 이름 목록
        template: 커스텀 템플릿 (None이면 기본 템플릿 사용)
                 템플릿에 {agent_tools} 플레이스홀더 포함 필요

    Returns:
        완성된 supervisor 프롬프트
    """
    handoff_tools = build_handoff_tools_section(child_names)

    if template:
        return template.format(agent_tools=handoff_tools)

    # 기본 supervisor 템플릿
    return f"""You are {profile.name}, a {profile.role} managing: {', '.join(child_names)}.

## Available Handoff Tools (IMPORTANT!)
{handoff_tools}

## Your Responsibilities
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

## CRITICAL RULES
1. To delegate a task, you MUST call the corresponding transfer tool
2. If you only output text without calling a tool, the delegation will fail
3. Always call a transfer tool after explaining your decision

Delegate tasks to the appropriate team member based on their expertise.
Respond in Korean."""


COORDINATOR_PROMPT_TEMPLATE = """You are a silent meeting coordinator.
You NEVER speak directly. You ONLY route to agents by calling transfer tools.

## Available Handoff Tools
{agent_tools}

## Routing Rules
1. Meeting start → transfer_to_host (Host does opening)
2. After Host opening → transfer_to_pm (status report)
3. After PM report → transfer_to_host (transition)
4. After Host transition → transfer_to_techlead (issue resolution)
5. Discussion moderation needed → transfer_to_host
6. After issue resolution → transfer_to_host (closing)
7. After Host closing → END (no tool call)

## CRITICAL
- Output NO text, ONLY tool calls
- Host handles all speaking and facilitation
- You are invisible to meeting participants
"""


def build_coordinator_prompt(agent_names: list[str]) -> str:
    """Coordinator(Silent Supervisor) 프롬프트 생성

    Args:
        agent_names: 라우팅 대상 에이전트 이름 목록

    Returns:
        Coordinator 프롬프트 문자열
    """
    agent_tools = build_handoff_tools_section(agent_names)
    return COORDINATOR_PROMPT_TEMPLATE.format(agent_tools=agent_tools)
