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
