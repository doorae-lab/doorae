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


def test_hierarchical_agent_profile():
    """계층적 Agent Profile 테스트"""
    # TechLead는 하위 에이전트를 가짐
    profiles = load_agent_profiles("config/agent_profiles.yaml")
    tech_lead = profiles["TechLead"]
    
    assert tech_lead.is_supervisor()
    assert len(tech_lead.agents) == 3  # Backend, Frontend, DevOps
    
    child_names = tech_lead.get_child_names()
    assert "Backend" in child_names
    assert "Frontend" in child_names
    assert "DevOps" in child_names
    
    # PM은 leaf 노드
    pm = profiles["PM"]
    assert not pm.is_supervisor()
    assert pm.get_child_names() == []


def test_nested_agent_profile():
    """중첩된 Agent Profile 재귀 테스트"""
    nested_profile = AgentProfile(
        name="TeamLead",
        role="team_lead",
        responsibilities=["팀 관리"],
        expertise=["리더십"],
        agents=[
            AgentProfile(
                name="SubAgent",
                role="sub_agent",
                responsibilities=["작업 수행"],
                expertise=["Python"]
            )
        ]
    )
    
    assert nested_profile.is_supervisor()
    assert len(nested_profile.agents) == 1
    assert nested_profile.agents[0].name == "SubAgent"
    assert not nested_profile.agents[0].is_supervisor()
