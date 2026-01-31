"""Tests for prompt builders"""

import pytest
from thetable.graph.prompts import (
    build_handoff_tools_section,
    build_supervisor_prompt
)
from thetable.core.profile import AgentProfile


def test_build_handoff_tools_section():
    """핸드오프 도구 섹션 생성 테스트"""
    result = build_handoff_tools_section(["Backend", "Frontend"])

    # langgraph-supervisor가 도구 이름을 소문자로 변환하므로 소문자로 확인
    assert "transfer_to_backend" in result
    assert "transfer_to_frontend" in result
    assert "Backend에게 작업 위임" in result
    assert "Frontend에게 작업 위임" in result


def test_build_handoff_tools_section_empty():
    """빈 목록 처리 테스트"""
    assert build_handoff_tools_section([]) == ""


def test_build_handoff_tools_section_single():
    """단일 에이전트 테스트"""
    result = build_handoff_tools_section(["Backend"])

    # langgraph-supervisor가 도구 이름을 소문자로 변환
    assert "transfer_to_backend" in result
    assert "Backend에게 작업 위임" in result
    # 단일 항목이므로 줄바꿈 없음
    assert "\n" not in result


def test_build_supervisor_prompt_default():
    """기본 템플릿 프롬프트 생성 테스트"""
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["코드 리뷰", "기술 의사결정"],
        expertise=["Python", "Architecture"],
        agents=[]
    )

    prompt = build_supervisor_prompt(profile, ["Backend", "Frontend"])

    # 핸드오프 도구 섹션 포함 확인 (소문자로 변환됨)
    assert "transfer_to_backend" in prompt
    assert "transfer_to_frontend" in prompt

    # CRITICAL RULES 포함 확인
    assert "CRITICAL RULES" in prompt
    assert "MUST call the corresponding transfer tool" in prompt

    # 책임 사항 포함 확인
    assert "코드 리뷰" in prompt
    assert "기술 의사결정" in prompt

    # 역할 정보 포함 확인
    assert "TechLead" in prompt
    assert "tech_lead" in prompt


def test_build_supervisor_prompt_custom_template():
    """커스텀 템플릿 프롬프트 생성 테스트 (Host용)"""
    profile = AgentProfile(
        name="Host",
        role="meeting_facilitator",
        responsibilities=["Phase 관리"],
        expertise=[],
        agents=[]
    )

    template = """Meeting Host Instructions:
{agent_tools}

Additional context here."""

    prompt = build_supervisor_prompt(profile, ["PM", "TechLead"], template=template)

    # 핸드오프 도구 포함 확인 (소문자로 변환됨)
    assert "transfer_to_pm" in prompt
    assert "transfer_to_techlead" in prompt

    # 커스텀 템플릿 구조 유지 확인
    assert "Meeting Host Instructions:" in prompt
    assert "Additional context here." in prompt

    # 기본 템플릿 내용은 없어야 함
    assert "CRITICAL RULES" not in prompt


def test_build_supervisor_prompt_no_children():
    """하위 에이전트 없는 경우 테스트"""
    profile = AgentProfile(
        name="Worker",
        role="worker",
        responsibilities=["작업 수행"],
        expertise=["Coding"],
        agents=[]
    )

    prompt = build_supervisor_prompt(profile, [])

    # 핸드오프 도구 섹션이 비어있어야 함
    assert "transfer_to_" not in prompt

    # 나머지 구조는 유지
    assert "Worker" in prompt
    assert "작업 수행" in prompt


def test_build_coordinator_prompt():
    """Coordinator 프롬프트 생성 테스트"""
    from thetable.graph.prompts import build_coordinator_prompt

    result = build_coordinator_prompt(["Host", "PM", "TechLead"])

    # 핸드오프 도구 포함 확인
    assert "transfer_to_host" in result
    assert "transfer_to_pm" in result
    assert "transfer_to_techlead" in result

    # Silent 규칙 포함 확인
    assert "NEVER" in result
    assert "NO text" in result or "ONLY" in result


def test_build_coordinator_prompt_empty():
    """빈 에이전트 목록 처리 테스트"""
    from thetable.graph.prompts import build_coordinator_prompt

    result = build_coordinator_prompt([])
    # 핸드오프 도구 섹션이 비어있어야 함 (템플릿 자체는 transfer_to_ 언급 가능)
    assert "## Available Handoff Tools\n\n" in result or "## Available Handoff Tools\n##" in result
