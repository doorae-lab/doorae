"""안건 기반 회의 워크플로우

아키텍처:
- pending_speakers 큐 기반 라우팅 (LLM 호출 최소화)
- 안건(Agenda) 중심의 구조화된 회의 진행
- participant → process_response 직선 구조 (요약은 agent 내부에서 langmem 인라인 호출)
- Host 명시적 안건 완료 선언
- AI 자동 안건 관리 (추가/수정/제거)
"""
import copy
import time
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END

from doorae.config import create_agent_llm, create_main_llm, create_task_llm, get_settings
from doorae.graph.state import MeetingState
from doorae.core.profile import AgentProfile, load_agent_profiles, merge_profiles_with_overrides
from doorae.graph.input_provider import CliInputProvider, InputProvider
from doorae.graph.nodes import (
    NodeRegistry,
    ProcessResponseNode,
    RefillSpeakersNode,
    condition_router,
    initialize_mcp_tools,
)
from doorae.graph.participant_registry import ParticipantRegistry


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    main_model: BaseChatModel = None,
    task_model: BaseChatModel = None,
    mcp_tools: dict[str, list] = None,
    input_provider: Optional[InputProvider] = None,
    profiles_override: Optional[dict[str, AgentProfile]] = None,
    participant_registry: Optional[ParticipantRegistry] = None,
):
    """안건 기반 회의 워크플로우 생성

    Args:
        profiles_path: agent_profiles.yaml 경로
        main_model: 회의 에이전트 응답 생성용 LLM (None이면 기본 모델 생성)
        task_model: 작은 작업용 LLM (None이면 기본 모델 생성)
        mcp_tools: 서버별 MCP tools 딕셔너리 {server_name: [tools]}
        input_provider: HumanNode 입력 제공자 (None이면 CLI 기본)
        profiles_override: 런타임에 추가/덮어쓸 프로필 딕셔너리

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """

    settings = get_settings()

    # Main model (refill_speakers용, 스트리밍 활성화)
    if main_model is None:
        main_model = create_main_llm(streaming=True)

    # Task model (유틸리티 작업용)
    if task_model is None:
        task_model = create_task_llm()

    if input_provider is None:
        input_provider = CliInputProvider()

    # 1. 프로필 로드 (+ 런타임 오버라이드)
    profiles = merge_profiles_with_overrides(
        load_agent_profiles(profiles_path),
        profiles_override,
    )
    participant_registry = participant_registry or ParticipantRegistry()
    for profile in profiles.values():
        participant_registry.add(profile)

    # 2. StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 3. refill_speakers 노드 추가
    refill_node = RefillSpeakersNode(
        model=main_model,
        valid_speakers=set(profiles.keys()),
        registry=participant_registry,
    )
    workflow.add_node("refill_speakers", refill_node)

    # 4. process_response 노드 추가
    process_node = ProcessResponseNode(
        model=task_model,
        valid_speakers=list(profiles.keys()),
        registry=participant_registry,
    )
    workflow.add_node("process_response", process_node)

    # 5. 단일 participant dispatch 노드 추가
    agent_models: dict[str, BaseChatModel] = {}
    for name, profile in profiles.items():
        if profile.is_human:
            continue
        if profile.llm is None:
            agent_models[name] = main_model
        else:
            agent_models[name] = create_agent_llm(
                profile=profile,
                settings=settings,
                streaming=True,
            )
    workflow.add_node(
        "participant",
        NodeRegistry.create(
            "dispatch",
            registry=participant_registry,
            input_provider=input_provider,
            agent_models=agent_models,
            mcp_tools=mcp_tools,
            settings=settings,
        ),
    )

    # 6. 진입점: refill_speakers
    workflow.set_entry_point("refill_speakers")

    # 7. participant → process_response (직선 구조, 요약은 agent 내부 인라인)
    workflow.add_edge("participant", "process_response")

    # 8. process_response → condition_router
    available_targets = {
        "participant": "participant",
        "refill_speakers": "refill_speakers",
        END: END,
    }

    workflow.add_conditional_edges(
        "process_response",
        condition_router,
        available_targets,
    )

    # 9. refill_speakers → condition_router
    workflow.add_conditional_edges(
        "refill_speakers",
        condition_router,
        available_targets,
    )

    # 10. 컴파일
    compiled_workflow = workflow.compile()
    setattr(compiled_workflow, "participant_registry", participant_registry)
    return compiled_workflow


def build_initial_state(
    settings,
    initial_message: str,
    human_names: list[str],
    agendas: list[dict],
) -> dict:
    """회의 초기 상태 구성."""
    base_agendas = copy.deepcopy(agendas)

    if base_agendas:
        base_agendas[0]["status"] = "in_progress"
        base_agendas[0]["start_time"] = time.time()
        for agenda in base_agendas[1:]:
            agenda["status"] = "pending"

    for agenda in base_agendas:
        required_speakers = agenda.setdefault("required_speakers", [])
        for human_name in human_names:
            if human_name not in required_speakers:
                required_speakers.append(human_name)

    return {
        "messages": [HumanMessage(content=initial_message)],
        "agendas": base_agendas,
        "current_agenda_idx": 0,
        "pending_proposals": [],
        "pending_speakers": [],
        "participants": {name: "participant" for name in human_names},
        "speaker_counts": {},
        "participant_statuses": {},
        "consecutive_host_delegations": 0,
        "turn_count": 0,
        "max_turns": settings.max_turns,
        "meeting_ended": False,
        "summary": None,
        "start_time": time.time(),
    }
