"""Prompt templates and builders for supervisors"""

from thetable.core.profile import AgentProfile


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


COORDINATOR_PROMPT_TEMPLATE = """You are a meeting coordinator. Your ONLY job is to decide who speaks next.

## Available Transfer Tools
{agent_tools}

## DECISION PROCESS (Follow these steps IN ORDER)

### Step 1: Check conversation history
Look at ALL messages, especially the MOST RECENT non-Coordinator message.

### Step 2: Detect mentions (HIGHEST PRIORITY)
If the last speaker mentioned ANYONE by name, transfer to that person immediately:
- "PM님" or "pm님" → transfer_to_pm
- "TechLead님" or "techlead님" → transfer_to_techlead
- "Host님" or "host님" → transfer_to_host
- "DevOps님" or "devops님" → transfer_to_devops
- "Designer님" or "designer님" → transfer_to_designer

### Step 3: Natural flow (if no mention)
- First turn: Always → transfer_to_host
- After Host intro: → transfer_to_pm (for project overview)
- After PM: → transfer_to_techlead (for technical review)
- After TechLead: → transfer_to_devops (for infrastructure)
- After DevOps: → transfer_to_designer (for UX/design)
- After Designer: → transfer_to_host (for summary)
- After Host summary: END (no tool call)

### Step 4: End condition
ONLY end the meeting if ALL of these are true:
- Host has said "회의를 마치겠습니다" or "종료" or provided a clear summary
- PM has spoken at least once
- TechLead has spoken at least once  
- At least 10 messages have been exchanged

Until then, keep following the natural flow (Step 3).

## Who has expertise in what?
- Host: 회의 진행, 요약
- PM: 일정, 리스크
- TechLead: 기술, 아키텍처  
- DevOps: 인프라, 배포
- Designer: UI/UX

## CRITICAL RULES
1. ALWAYS check for "님" mentions FIRST
2. Do NOT loop back to same person twice in a row
3. Follow natural conversation flow
4. When meeting is done, do NOT call any tool

## Response format
Just call the transfer tool - minimal or no text needed.
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
