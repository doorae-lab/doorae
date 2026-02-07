"""안건 기반 회의 워크플로우

아키텍처:
- pending_speakers 큐 기반 라우팅 (LLM 호출 최소화)
- 안건(Agenda) 중심의 구조화된 회의 진행
- LLM 기반 멘션 추출 및 의도 분석
- Host 명시적 안건 완료 선언
- AI 자동 안건 관리 (추가/수정/제거)
"""
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from loguru import logger

from thetable.config import create_main_llm, create_task_llm
from thetable.graph.state import MeetingState
from thetable.core.profile import load_agent_profiles
from thetable.graph.nodes import (
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
    mcp_tools: dict[str, list] = None
):
    """안건 기반 회의 워크플로우 생성

    Args:
        profiles_path: agent_profiles.yaml 경로
        main_model: 회의 에이전트 응답 생성용 LLM (None이면 기본 모델 생성)
        task_model: 작은 작업용 LLM (None이면 기본 모델 생성)
        mcp_tools: 서버별 MCP tools 딕셔너리 {server_name: [tools]}

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """

    # Main model (에이전트 응답 생성용, 스트리밍 활성화)
    if main_model is None:
        main_model = create_main_llm(streaming=True)

    # Task model (유틸리티 작업용)
    if task_model is None:
        task_model = create_task_llm()

    # 1. 프로필 로드
    profiles = load_agent_profiles(profiles_path)

    # 2. StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 3. refill_speakers 노드 추가
    refill_node = RefillSpeakersNode(model=main_model)
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
        node = NodeRegistry.create(
            node_type,
            profile=profile,
            model=main_model,
            all_agent_names=list(profiles.keys()),
            all_profiles=profiles,
            mcp_tools=mcp_tools,
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
