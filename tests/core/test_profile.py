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
    assert len(tech_lead.agents) == 2  # Backend, Frontend

    child_names = tech_lead.get_child_names()
    assert "Backend" in child_names
    assert "Frontend" in child_names
    
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


def test_host_profile_exists():
    """Host Agent Profile 존재 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")

    assert "Host" in profiles
    assert profiles["Host"].role == "host"

    # Host는 leaf 노드여야 함 (하위 에이전트 없음)
    assert not profiles["Host"].is_supervisor()
    assert profiles["Host"].get_child_names() == []


def test_host_profile_responsibilities():
    """Host Agent의 책임 및 전문성 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")
    host = profiles["Host"]

    # 회의 진행 관련 책임 확인
    assert "회의 진행 및 조율" in host.responsibilities
    assert "다음 발언자 선택" in host.responsibilities

    # 퍼실리테이션 전문성 확인
    assert "회의 퍼실리테이션" in host.expertise
    assert "시간 관리" in host.expertise
