import pytest
from doorae.core.profile import (
    AgentLLMConfig,
    AgentProfile,
    flatten_all_profiles,
    load_agent_profiles,
    validate_no_cycles,
)


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



def test_is_human_field_default():
    """is_human 필드 기본값 테스트"""
    profile = AgentProfile(
        name="TestAgent",
        role="test_role",
        responsibilities=["Test responsibility"],
        expertise=["Test expertise"]
    )
    
    # 기본값은 False
    assert profile.is_human is False


def test_is_human_field_explicit():
    """is_human 필드 명시적 설정 테스트"""
    ai_profile = AgentProfile(
        name="AIAgent",
        role="ai_role",
        responsibilities=["AI responsibility"],
        expertise=["AI expertise"],
        is_human=False
    )
    
    human_profile = AgentProfile(
        name="HumanUser",
        role="human_role",
        responsibilities=["Human responsibility"],
        expertise=["Human expertise"],
        is_human=True
    )
    
    assert ai_profile.is_human is False
    assert human_profile.is_human is True


def test_load_agent_profiles_from_yaml():
    """YAML에서 Agent Profile 로드 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")

    assert "PM" in profiles
    assert "TechLead" in profiles
    assert profiles["PM"].role == "project_manager"


def test_hierarchical_agent_profile():
    """계층적 Agent Profile 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")
    tech_lead = profiles["TechLead"]

    assert tech_lead.is_supervisor()
    assert tech_lead.get_child_names() == ["Backend", "Frontend"]

    # PM도 leaf 노드
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


def test_flatten_all_profiles_includes_nested_agents():
    profiles = load_agent_profiles("config/agent_profiles.yaml")
    flat_profiles = flatten_all_profiles(profiles)

    assert {"Host", "PM", "TechLead", "Backend", "Frontend"}.issubset(flat_profiles.keys())
    assert flat_profiles["Backend"].role == "backend_engineer"
    assert flat_profiles["Frontend"].role == "frontend_engineer"


def test_validate_no_cycles_raises_on_recursive_reference():
    profiles = {
        "A": AgentProfile(
            name="A",
            role="lead",
            responsibilities=["coordination"],
            expertise=["planning"],
            agents=[
                AgentProfile(
                    name="B",
                    role="worker",
                    responsibilities=["execute"],
                    expertise=["python"],
                    agents=[
                        AgentProfile(
                            name="A",
                            role="lead",
                            responsibilities=["coordination"],
                            expertise=["planning"],
                        )
                    ],
                )
            ],
        )
    }

    with pytest.raises(ValueError, match="Agent cycle detected"):
        validate_no_cycles(profiles)


def test_host_profile_responsibilities():
    """Host Agent의 책임 및 전문성 테스트"""
    profiles = load_agent_profiles("config/agent_profiles.yaml")
    host = profiles["Host"]

    # 회의 진행 관련 책임 확인
    assert "회의 시작 인사 및 안건 소개" in host.responsibilities
    assert "안건 완료 시 다음 안건으로 전환 안내" in host.responsibilities
    assert "토론 중재 및 의견 요청" in host.responsibilities
    assert "회의 요약 및 마무리" in host.responsibilities

    # 퍼실리테이션 전문성 확인
    assert "회의 퍼실리테이션" in host.expertise
    assert "갈등 조정" in host.expertise
    assert "시간 관리" in host.expertise


def test_agent_profile_llm_config_optional():
    profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계"],
        expertise=["Python"],
    )
    assert profile.llm is None


def test_agent_profile_llm_config_loaded():
    profile = AgentProfile(
        name="PM",
        role="project_manager",
        responsibilities=["일정"],
        expertise=["관리"],
        llm={
            "model": "gpt-4.1-mini",
            "api_key": "test-key",
            "base_url": "https://example.ai/v1",
            "temperature": 0.2,
            "max_tokens": 512,
        },
    )

    assert isinstance(profile.llm, AgentLLMConfig)
    assert profile.llm.model == "gpt-4.1-mini"
    assert profile.llm.api_key == "test-key"
    assert profile.llm.base_url == "https://example.ai/v1"
    assert profile.llm.temperature == 0.2
    assert profile.llm.max_tokens == 512


def test_agent_llm_config_resolves_env_vars(monkeypatch):
    """${VAR} 패턴이 환경변수 값으로 치환된다"""
    monkeypatch.setenv("MY_API_KEY", "sk-real-key-123")
    monkeypatch.setenv("MY_BASE_URL", "https://api.example.com/v1")

    config = AgentLLMConfig(
        api_key="${MY_API_KEY}",
        base_url="${MY_BASE_URL}",
        model="gpt-4.1-mini",
    )

    assert config.api_key == "sk-real-key-123"
    assert config.base_url == "https://api.example.com/v1"
    assert config.model == "gpt-4.1-mini"  # 일반 문자열은 그대로


def test_agent_llm_config_unset_env_var_becomes_none(monkeypatch):
    """존재하지 않는 환경변수 참조 시 None으로 fallback"""
    monkeypatch.delenv("NONEXISTENT_KEY", raising=False)

    config = AgentLLMConfig(
        api_key="${NONEXISTENT_KEY}",
    )

    assert config.api_key is None


def test_agent_profile_hierarchy_roundtrip():
    """계층적 프로필 직렬화/역직렬화 라운드트립 테스트."""
    supervisor = AgentProfile(
        name="PM팀장",
        role="project_manager",
        responsibilities=["프로젝트 관리"],
        expertise=["일정 관리"],
        agents=[
            AgentProfile(
                name="기획자",
                role="planner",
                responsibilities=["기획"],
                expertise=["기획"],
            ),
            AgentProfile(
                name="디자이너",
                role="designer",
                responsibilities=["디자인"],
                expertise=["UI/UX"],
            ),
        ],
    )

    # Serialize
    dumped = supervisor.model_dump(exclude={"llm"})

    # Deserialize
    restored = AgentProfile.model_validate(dumped)

    assert restored.name == "PM팀장"
    assert len(restored.agents) == 2
    assert restored.agents[0].name == "기획자"
    assert restored.agents[1].name == "디자이너"
    assert restored.is_supervisor()


def test_agent_profile_hierarchy_flatten_after_roundtrip():
    """라운드트립 후 flatten이 정상 동작하는지 테스트."""
    profiles = {
        "PM팀장": AgentProfile(
            name="PM팀장",
            role="project_manager",
            responsibilities=["프로젝트 관리"],
            expertise=["일정 관리"],
            agents=[
                AgentProfile(
                    name="기획자",
                    role="planner",
                    responsibilities=["기획"],
                    expertise=["기획"],
                ),
            ],
        ),
    }

    # Serialize and deserialize
    serialized = {name: p.model_dump(exclude={"llm"}) for name, p in profiles.items()}
    restored = {name: AgentProfile.model_validate(d) for name, d in serialized.items()}

    # Flatten should work
    flat = flatten_all_profiles(restored)
    assert "PM팀장" in flat
    assert "기획자" in flat
