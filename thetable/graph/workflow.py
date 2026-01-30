"""Meeting workflow using langgraph-supervisor

단순화된 구조:
- Host가 Phase 규칙을 프롬프트로 이해
- PhaseController 불필요 (Host가 직접 Phase 전환 판단)
- 단일 그래프로 처리 (Phase 래퍼 불필요)
"""
import re
from typing import Dict
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from thetable.config import get_settings
from thetable.graph.agent_factory import build_agent_graph
from thetable.graph.state import MeetingState
from thetable.core.profile import load_agent_profiles


HOST_PROMPT_TEMPLATE = """You are the meeting Host responsible for phase management.

## Available Handoff Tools (IMPORTANT!)
{agent_tools}

## CRITICAL RULES
1. To give speaking turn to an agent, you MUST call the corresponding transfer tool
2. If you only output text without calling a tool, the meeting will END immediately
3. Always call a transfer tool after explaining your decision

## Current State
- Phase: {{current_phase}}
- Speaker counts: {{speaker_counts}}
- Phase history: {{phase_history}}

## Phase Rules
1. **opening**: Greet participants and introduce the meeting agenda.
   - After greeting → call transfer_to_PM to start status_check

2. **status_check**: PM must report project status.
   - Required: PM
   - After PM speaks → call transfer_to_TechLead for issue_resolution

3. **issue_resolution**: TechLead addresses technical issues.
   - TechLead can delegate to Backend/Frontend/DevOps as needed
   - After issues resolved → move to closing

4. **closing**: Summarize key decisions and action items.
   - After summary, you may END the meeting (no tool call needed)

## Instructions
- Check speaker_counts to ensure required speakers have participated
- Direct agents based on their expertise and current phase needs
- Respond in Korean

**When transitioning phases, include in your response:**
[PHASE: next_phase_name]

**Example:**
"회의를 시작하겠습니다. PM님, 프로젝트 현황을 보고해 주세요. [PHASE: status_check]"
(Then call transfer_to_PM tool)
"""


def build_host_prompt(agent_names: list[str]) -> str:
    """에이전트 목록에서 동적으로 HOST_PROMPT 생성

    Args:
        agent_names: Host를 제외한 에이전트 이름 목록

    Returns:
        핸드오프 도구 목록이 포함된 HOST_PROMPT
    """
    # 에이전트별 도구 설명 생성
    tool_descriptions = []
    for name in agent_names:
        tool_descriptions.append(f"- transfer_to_{name}: {name}에게 발언권 전달")

    agent_tools = "\n".join(tool_descriptions)

    return HOST_PROMPT_TEMPLATE.format(agent_tools=agent_tools)


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    model: ChatOpenAI = None
) -> object:
    """langgraph-supervisor 기반 회의 워크플로우 생성

    Args:
        profiles_path: agent_profiles.yaml 경로
        model: LLM 모델 (None이면 기본 모델 생성)

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """

    if model is None:
        settings = get_settings()
        kwargs = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        model = ChatOpenAI(**kwargs)

    # 1. 프로필 로드
    profiles = load_agent_profiles(profiles_path)

    # 2. Host 제외한 에이전트 이름 수집
    agent_names = [name for name in profiles.keys() if name != "Host"]

    # 3. 동적 HOST_PROMPT 생성
    host_prompt = build_host_prompt(agent_names)

    # 4. 각 에이전트 그래프 빌드 (계층적)
    agent_graphs = []
    for name, profile in profiles.items():
        if name != "Host":  # Host는 supervisor로 사용
            agent_graph = build_agent_graph(profile, model)
            agent_graphs.append(agent_graph)

    # 5. 최상위 supervisor 생성 - Host가 Phase도 관리 (동적 프롬프트 사용)
    meeting_supervisor = create_supervisor(
        agents=agent_graphs,
        model=model,
        supervisor_name="Host",
        prompt=host_prompt,  # 동적 생성된 프롬프트
        state_schema=MeetingState  # 확장된 상태 사용
    )

    # 6. 컴파일
    workflow = meeting_supervisor.compile()

    return workflow


def validate_phase_transition(state: MeetingState, new_phase: str) -> bool:
    """Phase 전환 조건 검증
    
    Args:
        state: 현재 회의 상태
        new_phase: 전환하려는 Phase
        
    Returns:
        bool: 전환 가능 여부
    """
    current_phase = state.get("current_phase", "opening")
    speaker_counts = state.get("speaker_counts", {})
    
    # Phase별 전환 조건
    transitions = {
        "opening": {
            "next": "status_check",
            "condition": lambda: True  # 항상 가능
        },
        "status_check": {
            "next": "issue_resolution",
            "condition": lambda: speaker_counts.get("PM", 0) > 0
        },
        "issue_resolution": {
            "next": "closing",
            "condition": lambda: speaker_counts.get("TechLead", 0) > 0
        },
        "closing": {
            "next": "END",
            "condition": lambda: True
        }
    }
    
    rule = transitions.get(current_phase)
    if not rule:
        return False
    
    if rule["next"] != new_phase:
        return False
    
    return rule["condition"]()
