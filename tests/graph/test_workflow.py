"""Tests for workflow"""
import pytest
import re
from thetable.graph.workflow import (
    validate_phase_transition,
    build_host_prompt,
    HOST_PROMPT_TEMPLATE
)
from thetable.graph.state import MeetingState


def test_build_host_prompt():
    """build_host_prompt 함수가 올바른 도구 목록 생성하는지 확인"""
    agent_names = ["PM", "TechLead", "DevOps"]
    prompt = build_host_prompt(agent_names)

    # 각 에이전트에 대한 transfer 도구가 포함되어 있는지 확인
    assert "transfer_to_PM" in prompt
    assert "transfer_to_TechLead" in prompt
    assert "transfer_to_DevOps" in prompt

    # CRITICAL RULES 섹션이 포함되어 있는지 확인
    assert "CRITICAL RULES" in prompt
    assert "To give speaking turn to an agent, you MUST call the corresponding transfer tool" in prompt

    # Phase 규칙이 포함되어 있는지 확인
    assert "opening" in prompt
    assert "status_check" in prompt
    assert "issue_resolution" in prompt
    assert "closing" in prompt


def test_build_host_prompt_empty_agents():
    """빈 에이전트 목록으로도 정상 작동하는지 확인"""
    agent_names = []
    prompt = build_host_prompt(agent_names)

    # 프롬프트가 생성되어야 함
    assert len(prompt) > 0
    assert "CRITICAL RULES" in prompt

    # 도구 목록은 비어있어야 함 (헤더만 있음)
    assert "Available Handoff Tools" in prompt


def test_build_host_prompt_single_agent():
    """단일 에이전트로도 정상 작동하는지 확인"""
    agent_names = ["PM"]
    prompt = build_host_prompt(agent_names)

    assert "transfer_to_PM" in prompt
    assert "PM에게 발언권 전달" in prompt


def test_host_prompt_template_placeholders():
    """HOST_PROMPT_TEMPLATE에 올바른 플레이스홀더가 있는지 확인"""
    # 동적 치환용 {agent_tools}
    assert "{agent_tools}" in HOST_PROMPT_TEMPLATE

    # 런타임 치환용 {{current_phase}} 등
    assert "{{current_phase}}" in HOST_PROMPT_TEMPLATE
    assert "{{speaker_counts}}" in HOST_PROMPT_TEMPLATE
    assert "{{phase_history}}" in HOST_PROMPT_TEMPLATE


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


def test_create_meeting_workflow_integration():
    """create_meeting_workflow 통합 테스트"""
    from thetable.graph.workflow import create_meeting_workflow

    # 워크플로우 생성
    workflow = create_meeting_workflow()

    # 워크플로우가 정상적으로 생성되었는지 확인
    assert workflow is not None

    # CompiledGraph의 기본 속성 확인
    assert hasattr(workflow, 'invoke') or hasattr(workflow, 'ainvoke')
