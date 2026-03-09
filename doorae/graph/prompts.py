"""Prompt templates and builders for supervisors"""

from doorae.core.profile import AgentProfile


def build_handoff_tools_section(child_names: list[str]) -> str:
    """핸드오프 도구 문서 섹션 생성

    Args:
        child_names: 하위 에이전트 이름 목록

    Returns:
        핸드오프 도구 설명 문자열

    Note:
        도구 이름은 에이전트 이름을 소문자로 변환하여 생성됩니다.
        예: 'TechLead' → 'transfer_to_techlead'
    """
    if not child_names:
        return ""

    tool_descriptions = []
    for name in child_names:
        # 에이전트 이름을 소문자로 변환
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
