"""서버용 회의 워크플로우."""

import asyncio
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from thetable.config import create_main_llm
from thetable.core.profile import AgentProfile
from thetable.graph.state import MeetingState
from thetable.graph.nodes import NodeRegistry
from thetable.server.user_input_node import UserInputNode


def create_server_workflow(
    input_queue: asyncio.Queue,
    username: str,
    agent_profile: AgentProfile,
    main_model: BaseChatModel = None,
    mcp_tools: dict[str, list] = None,
):
    """서버용 회의 워크플로우 생성.

    Args:
        input_queue: 사용자 입력을 받는 asyncio.Queue
        username: 사용자 이름
        agent_profile: AI 에이전트 프로필
        main_model: 에이전트 응답 생성용 LLM (None이면 기본 모델 생성)
        mcp_tools: 서버별 MCP tools 딕셔너리 {server_name: [tools]}

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """
    # Main model 생성
    if main_model is None:
        main_model = create_main_llm(streaming=True)

    # StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 1. 사용자 입력 노드 추가 (직접 인스턴스화)
    user_node = UserInputNode(input_queue=input_queue, username=username)
    workflow.add_node("user", user_node)

    # 2. AI 에이전트 노드 추가
    agent_node = NodeRegistry.create(
        "agent",
        profile=agent_profile,
        model=main_model,
        all_agent_names=[username, agent_profile.name],
        all_profiles={
            username: AgentProfile(
                name=username,
                role="참여자",
                responsibilities=["회의 참여"],
                expertise=["일반"],
                is_human=True
            ),
            agent_profile.name: agent_profile,
        },
        mcp_tools=mcp_tools,
    )
    workflow.add_node("agent", agent_node)

    # 3. 엣지 설정: user → agent → END
    workflow.set_entry_point("user")
    workflow.add_edge("user", "agent")
    workflow.add_edge("agent", END)

    # 컴파일
    return workflow.compile()
