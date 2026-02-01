"""Tests for MeetingState definition"""
from thetable.graph.state import MeetingState, AgentInfo
from langgraph.graph import MessagesState


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
    """MeetingState 구조 테스트 (MessagesState 상속)"""
    from typing import get_type_hints
    hints = get_type_hints(MeetingState)

    assert 'messages' in hints
    assert 'agendas' in hints
    assert 'current_agenda_idx' in hints
    assert 'pending_speakers' in hints
    assert 'speaker_counts' in hints
    assert 'consecutive_host_delegations' in hints


def test_meeting_state_inherits_messages_state():
    """MeetingState가 MessagesState를 상속하는지 테스트"""
    from typing import get_type_hints
    
    # MeetingState가 MessagesState의 필드를 포함하는지 확인
    hints = get_type_hints(MeetingState)
    
    # MessagesState의 필수 필드인 'messages' 확인
    assert 'messages' in hints
    
    # MeetingState의 추가 필드 확인
    assert 'agendas' in hints
    assert 'pending_speakers' in hints


def test_meeting_state_inherits_messages_state():
    """MeetingState가 MessagesState를 상속하는지 테스트"""
    from typing import get_type_hints
    
    # MeetingState가 MessagesState의 필드를 포함하는지 확인
    hints = get_type_hints(MeetingState)
    
    # MessagesState의 필수 필드인 'messages' 확인
    assert 'messages' in hints
    
    # MeetingState의 추가 필드 확인
    assert 'agendas' in hints
    assert 'pending_speakers' in hints


def test_meeting_state_defaults():
    """MeetingState 기본값 테스트"""
    # MeetingState 인스턴스 생성 (TypedDict로 사용)
    state: MeetingState = {
        "messages": [],
        "agendas": [],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }
    
    assert state["current_agenda_idx"] == 0
    assert len(state["messages"]) == 0
    assert len(state["speaker_counts"]) == 0
    assert len(state["pending_speakers"]) == 0
