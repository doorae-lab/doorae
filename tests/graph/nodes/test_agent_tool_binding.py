from unittest.mock import AsyncMock, MagicMock
from typing import cast

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from doorae.core.profile import AgentProfile
from doorae.graph.nodes.agent import AgentNode
from doorae.graph.state import MeetingState


def _create_node(name: str, role: str) -> tuple[AgentNode, AsyncMock]:
    profile = AgentProfile(
        name=name,
        role=role,
        responsibilities=["test"],
        expertise=["test"],
    )
    node = AgentNode(profile=profile, model=MagicMock())
    invoke_with_tools_mock: AsyncMock = AsyncMock(
        return_value=AIMessage(content="테스트 응답", name=name)
    )
    node.agent.invoke_with_tools = invoke_with_tools_mock
    return node, invoke_with_tools_mock


def _create_state(pending_proposals: list[dict[str, str]]) -> MeetingState:
    return {
        "messages": [HumanMessage(content="회의 시작")],
        "agendas": [{"title": "테스트", "status": "in_progress"}],
        "current_agenda_idx": 0,
        "summary": "",
        "pending_proposals": pending_proposals,
        "pending_speakers": [],
        "speaker_counts": {},
        "participant_statuses": {},
        "consecutive_host_delegations": 0,
        "turn_count": 0,
        "max_turns": 1000,
        "meeting_ended": False,
        "start_time": 0.0,
    }


def _tool_names_from_call(invoke_with_tools_mock: AsyncMock) -> list[str]:
    call_args = invoke_with_tools_mock.call_args
    assert call_args is not None
    extra_tools = cast(list[object], call_args.kwargs.get("extra_tools", []))
    return [cast(str, getattr(tool, "name")) for tool in extra_tools]


@pytest.mark.asyncio
async def test_non_host_agent_gets_only_propose_tool():
    node, invoke_with_tools_mock = _create_node(name="PM", role="project_manager")
    state = _create_state(
        [{"title": "제안1", "proposed_by": "PM", "status": "pending"}]
    )

    _ = await node.execute(state)

    tool_names = _tool_names_from_call(invoke_with_tools_mock)
    assert tool_names == ["propose_agenda"]


@pytest.mark.asyncio
async def test_host_with_empty_pending_gets_only_propose_tool():
    node, invoke_with_tools_mock = _create_node(name="Host", role="host")
    state = _create_state([])

    _ = await node.execute(state)

    tool_names = _tool_names_from_call(invoke_with_tools_mock)
    assert tool_names == ["propose_agenda"]


@pytest.mark.asyncio
async def test_host_with_pending_gets_propose_approve_reject_tools():
    node, invoke_with_tools_mock = _create_node(name="Host", role="host")
    state = _create_state(
        [{"title": "제안1", "proposed_by": "PM", "status": "pending"}]
    )

    _ = await node.execute(state)

    tool_names = _tool_names_from_call(invoke_with_tools_mock)
    assert set(tool_names) == {"propose_agenda", "approve_agenda", "reject_agenda"}
    assert len(tool_names) == 3


@pytest.mark.asyncio
async def test_supervisor_agent_gets_sub_agent_tools():
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["리드"],
        expertise=["설계"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 구현"],
                expertise=["Python"],
            ),
            AgentProfile(
                name="Frontend",
                role="frontend_engineer",
                responsibilities=["UI 구현"],
                expertise=["React"],
            ),
        ],
    )
    node = AgentNode(profile=profile, model=MagicMock())
    invoke_with_tools_mock: AsyncMock = AsyncMock(
        return_value=AIMessage(content="테스트 응답", name="TechLead")
    )
    node.agent.invoke_with_tools = invoke_with_tools_mock

    result = await node.execute(_create_state([]))

    tool_names = _tool_names_from_call(invoke_with_tools_mock)
    assert "propose_agenda" in tool_names
    assert "ask_backend" in tool_names
    assert "ask_frontend" in tool_names
    assert cast(dict[str, str], result["participant_statuses"])["TechLead"] == "idle"
