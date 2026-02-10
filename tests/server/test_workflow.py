"""서버 워크플로우 테스트."""

import asyncio
import pytest
from unittest.mock import Mock
from thetable.core.profile import AgentProfile
from thetable.server.workflow import create_server_workflow


@pytest.mark.asyncio
async def test_create_server_workflow():
    """서버 워크플로우 생성 테스트."""
    input_queue = asyncio.Queue()
    agent_profile = AgentProfile(
        name="Assistant",
        role="회의 보조",
        responsibilities=["회의 진행 보조"],
        expertise=["대화 관리"],
        is_human=False,
    )

    # Mock LLM
    mock_llm = Mock()
    mock_llm.ainvoke = Mock(return_value=Mock(content="Test response"))

    workflow = create_server_workflow(
        input_queue=input_queue,
        username="Alice",
        agent_profile=agent_profile,
        main_model=mock_llm,
    )

    # 워크플로우가 정상적으로 생성되었는지 확인
    assert workflow is not None
    assert hasattr(workflow, "invoke")
    assert hasattr(workflow, "ainvoke")


@pytest.mark.asyncio
async def test_workflow_has_required_nodes():
    """워크플로우에 필수 노드가 있는지 테스트."""
    input_queue = asyncio.Queue()
    agent_profile = AgentProfile(
        name="Assistant",
        role="회의 보조",
        responsibilities=["회의 진행 보조"],
        expertise=["대화 관리"],
        is_human=False,
    )

    # Mock LLM
    mock_llm = Mock()

    workflow = create_server_workflow(
        input_queue=input_queue,
        username="Alice",
        agent_profile=agent_profile,
        main_model=mock_llm,
    )

    # 워크플로우 그래프 구조 확인
    graph = workflow.get_graph()
    node_names = [node.id for node in graph.nodes.values()]

    assert "user" in node_names
    assert "agent" in node_names
