import pytest
from unittest.mock import AsyncMock, MagicMock
from thetable.graph.nodes import supervisor_node
from thetable.graph.state import MeetingState, AgentInfo


@pytest.fixture
def mock_supervisor():
    """Mock supervisor agent"""
    supervisor = MagicMock()
    supervisor.select_next_speaker = AsyncMock(return_value={
        "next_speaker": "PM",
        "task": "@PM 현황을 보고하세요",
        "reason": "status_check phase"
    })
    return supervisor


@pytest.fixture
def meeting_state():
    """Test meeting state"""
    return {
        "messages": [],
        "current_phase": "status_check",
        "agents": [
            AgentInfo(name="PM", role="project_manager", profile_key="PM"),
            AgentInfo(name="TechLead", role="tech_lead", profile_key="TechLead")
        ],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0,
        "phase_history": []
    }


@pytest.fixture
def mock_agent():
    """Mock agent"""
    agent = MagicMock()
    agent.name = "PM"
    agent.generate_response = AsyncMock(return_value="프로젝트 진행 중입니다")
    return agent


@pytest.mark.asyncio
async def test_supervisor_node(mock_supervisor, meeting_state, monkeypatch):
    """Supervisor 노드 실행 테스트"""
    monkeypatch.setattr(
        "thetable.graph.nodes.get_supervisor",
        lambda state: mock_supervisor
    )

    result = await supervisor_node(meeting_state)

    assert result["next_speaker"] == "PM"
    assert "@PM" in result["current_task"]



@pytest.mark.asyncio
async def test_agent_node_factory(mock_agent, meeting_state, monkeypatch):
    """Agent 노드 팩토리 테스트"""
    from thetable.graph.nodes import create_agent_node

    monkeypatch.setattr(
        "thetable.graph.nodes.get_agent",
        lambda state, name: mock_agent
    )

    pm_node = create_agent_node("PM")
    meeting_state["current_task"] = "@PM 현황을 보고하세요"

    result = await pm_node(meeting_state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert result["messages"][0].name == "PM"
    assert result["messages"][0].content == "프로젝트 진행 중입니다"
