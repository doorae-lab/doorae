"""Tests for MeetingState definition"""
from thetable.graph.state import MeetingState, AgentInfo


def test_agent_info_creation():
    """AgentInfo 생성 테스트"""
    agent = AgentInfo(
        name="PM",
        role="project_manager",
        profile_key="PM"
    )

    assert agent.name == "PM"
    assert agent.role == "project_manager"


def test_meeting_state_structure():
    """MeetingState 구조 테스트"""
    from typing import get_type_hints
    hints = get_type_hints(MeetingState)

    assert 'messages' in hints
    assert 'current_phase' in hints
    assert 'agents' in hints
    assert 'next_speaker' in hints
