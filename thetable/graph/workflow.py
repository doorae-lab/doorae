"""Meeting workflow using langgraph-supervisor

단순화된 구조:
- Coordinator가 Silent Supervisor 역할 (라우팅만)
- Host는 다른 에이전트와 동일하게 YAML에서 정의
- 모든 에이전트를 동일하게 처리 (특별 분기 없음)
"""
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from thetable.config import get_settings
from thetable.graph.agent_factory import build_agent_graph
from thetable.graph.state import MeetingState
from thetable.core.profile import load_agent_profiles
from thetable.graph.prompts import build_coordinator_prompt
from thetable.graph.handoff_hook import create_handoff_hook


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

    # 2. 모든 에이전트 이름 수집
    agent_names = list(profiles.keys())

    # 3. Coordinator 프롬프트 생성
    coordinator_prompt = build_coordinator_prompt(agent_names)

    # 4. 모든 에이전트 그래프 빌드 (Host 포함, 특별 처리 없음)
    # 모든 에이전트에게 참여자 목록을 전달하여 서로를 언급할 수 있도록 함
    agent_graphs = []
    for name, profile in profiles.items():
        agent_graph = build_agent_graph(profile, model, agent_names)
        agent_graphs.append(agent_graph)

    # 5. Coordinator(Silent Supervisor) 생성
    # post_model_hook으로 판단 계층 주입
    handoff_hook = create_handoff_hook(agent_names)

    meeting_supervisor = create_supervisor(
        agents=agent_graphs,
        model=model,
        supervisor_name="Coordinator",
        prompt=coordinator_prompt,
        state_schema=MeetingState,
        post_model_hook=handoff_hook,  # 텍스트 출력 시 도구 호출 주입
        add_handoff_back_messages=False  # Flat 구조: transfer_back 메시지 비활성화
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

    transitions = {
        "opening": {
            "next": "status_check",
            "condition": lambda: True
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
