"""Tests for workflow"""
import pytest
import re
from thetable.graph.workflow import (
    validate_phase_transition,
    HOST_PROMPT
)
from thetable.graph.state import MeetingState


def test_host_prompt_contains_phase_rules():
    """Host 프롬프트에 Phase 규칙 포함 확인"""
    assert "opening" in HOST_PROMPT
    assert "status_check" in HOST_PROMPT
    assert "issue_resolution" in HOST_PROMPT
    assert "closing" in HOST_PROMPT
    assert "[PHASE:" in HOST_PROMPT


def test_phase_transition_opening_to_status_check():
    """opening → status_check 전환 테스트"""
    state: MeetingState = {
        "messages": [],
        "current_phase": "opening",
        "phase_history": [],
        "agents": [],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }
    
    # opening → status_check는 항상 가능
    assert validate_phase_transition(state, "status_check")


def test_phase_transition_status_check_requires_pm():
    """status_check → issue_resolution은 PM 발언 필요"""
    state: MeetingState = {
        "messages": [],
        "current_phase": "status_check",
        "phase_history": ["opening"],
        "agents": [],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},  # PM 발언 없음
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }
    
    # PM 발언 없으면 전환 불가
    assert not validate_phase_transition(state, "issue_resolution")
    
    # PM 발언 후에는 전환 가능
    state["speaker_counts"]["PM"] = 1
    assert validate_phase_transition(state, "issue_resolution")


def test_phase_transition_issue_resolution_requires_tech_lead():
    """issue_resolution → closing은 TechLead 발언 필요"""
    state: MeetingState = {
        "messages": [],
        "current_phase": "issue_resolution",
        "phase_history": ["opening", "status_check"],
        "agents": [],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {"PM": 1},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }
    
    # TechLead 발언 없으면 전환 불가
    assert not validate_phase_transition(state, "closing")
    
    # TechLead 발언 후에는 전환 가능
    state["speaker_counts"]["TechLead"] = 1
    assert validate_phase_transition(state, "closing")


def test_phase_transition_invalid():
    """잘못된 Phase 전환 테스트"""
    state: MeetingState = {
        "messages": [],
        "current_phase": "opening",
        "phase_history": [],
        "agents": [],
        "next_speaker": None,
        "current_task": None,
        "speaker_counts": {},
        "pending_mentions": [],
        "phase_required_speakers": {},
        "phase_goals": {},
        "start_time": 0.0,
        "phase_start_time": 0.0
    }
    
    # opening → closing 직접 전환 불가
    assert not validate_phase_transition(state, "closing")
    
    # opening → issue_resolution 직접 전환 불가
    assert not validate_phase_transition(state, "issue_resolution")
