import pytest
from thetable.core.profile import AgentProfile, load_agent_profiles


def test_agent_profile_creation():
    """Agent Profile 생성 테스트"""
    profile = AgentProfile(
        name="PM",
        role="project_manager",
        responsibilities=["프로젝트 일정 관리", "진행 상황 보고"],
        expertise=["일정 계획", "자원 관리"],
        phase_triggers={"status_check": "자동 발언"}
    )

    assert profile.name == "PM"
    assert profile.role == "project_manager"
    assert len(profile.responsibilities) == 2
    assert "status_check" in profile.phase_triggers


def test_load_agent_profiles_from_yaml():
    """YAML에서 Agent Profile 로드 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")

    assert "PM" in profiles
    assert "TechLead" in profiles
    assert profiles["PM"].role == "project_manager"
