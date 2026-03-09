"""안건 기반 회의 워크플로우

아키텍처:
- pending_speakers 큐 기반 라우팅 (LLM 호출 최소화)
- 안건(Agenda) 중심의 구조화된 회의 진행
- LLM 기반 멘션 추출 및 의도 분석
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
    SummarizationNode,
    condition_router,
    initialize_mcp_tools,
)


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    main_model: BaseChatModel = None,
    task_model: BaseChatModel = None,
    mcp_tools: dict[str, list] = None,
    input_provider: Optional[InputProvider] = None,
    profiles_override: Optional[dict[str, AgentProfile]] = None,
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

    # 2. StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 3. refill_speakers 노드 추가
    refill_node = RefillSpeakersNode(model=main_model, valid_speakers=set(profiles.keys()))
    workflow.add_node("refill_speakers", refill_node)

    # 4. summarize 노드 추가
    summarize_node = SummarizationNode(model=task_model)
    workflow.add_node("summarize", summarize_node)

    # 5. process_response 노드 추가
    process_node = ProcessResponseNode(
        model=task_model,
        valid_speakers=list(profiles.keys())
    )
    workflow.add_node("process_response", process_node)

    # 6. 각 에이전트 노드 추가 (NodeRegistry 활용)
    for name, profile in profiles.items():
        node_type = "human" if profile.is_human else "agent"
        if profile.is_human:
            node_model = None
        elif profile.llm is None:
            # Keep backwards compatibility: caller-provided main_model should still
            # drive agent turns when no per-agent LLM override is configured.
            node_model = main_model
        else:
            node_model = create_agent_llm(profile=profile, settings=settings, streaming=True)
        node = NodeRegistry.create(
            node_type,
            profile=profile,
            model=node_model,
            all_agent_names=list(profiles.keys()),
            all_profiles=profiles,
            mcp_tools=mcp_tools,
            input_provider=input_provider,
        )
        workflow.add_node(name.lower(), node)

    # 7. 진입점: refill_speakers
    workflow.set_entry_point("refill_speakers")

    # 8. 에이전트 → summarize → process_response
    for name in profiles.keys():
        workflow.add_edge(name.lower(), "summarize")

    workflow.add_edge("summarize", "process_response")

    # 9. process_response → condition_router
    available_targets = {name.lower(): name.lower() for name in profiles.keys()}
    available_targets["refill_speakers"] = "refill_speakers"
    available_targets[END] = END

    workflow.add_conditional_edges(
        "process_response",
        condition_router,
        available_targets
    )

    # 10. refill_speakers → condition_router
    workflow.add_conditional_edges(
        "refill_speakers",
        condition_router,
        available_targets
    )

    # 11. 컴파일
    return workflow.compile()


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
        "speaker_counts": {},
        "participant_statuses": {},
        "consecutive_host_delegations": 0,
        "turn_count": 0,
        "max_turns": settings.max_turns,
        "meeting_ended": False,
        "summary": "",
        "start_time": time.time(),
    }
