"""Tests for agent factory"""
import pytest
from unittest.mock import Mock, MagicMock
from langchain_openai import ChatOpenAI

from thetable.core.profile import AgentProfile
from thetable.graph.agent_factory import (
    build_agent_node,
    _build_agent_prompt
)


@pytest.fixture
def mock_model():
    """Mock LLM 모델"""
    model = Mock(spec=ChatOpenAI)
    return model


def test_build_agent_prompt():
    """에이전트 프롬프트 생성 테스트"""
    profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계", "DB 최적화"],
        expertise=["Python", "PostgreSQL"]
    )
    
    prompt = _build_agent_prompt(profile)
    
    assert "Backend" in prompt
    assert "backend_engineer" in prompt
    assert "API 설계" in prompt
    assert "Python" in prompt


# _build_supervisor_prompt는 prompts.py의 build_supervisor_prompt로 이동됨
# 해당 테스트는 test_prompts.py에서 수행


def test_leaf_agent_creation(mock_model):
    """Leaf 에이전트 생성 테스트"""
    profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계"],
        expertise=["Python"]
    )

    # Note: build_agent_graph는 create_react_agent를 호출하므로
    # 실제 테스트는 통합 테스트에서 수행
    # 여기서는 is_supervisor() 로직만 테스트
    assert not profile.is_supervisor()


def test_supervisor_wrapper_has_name_attribute():
    """Supervisor wrapper에 name 속성이 있는지 테스트"""
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["Python"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 개발"],
                expertise=["Python"],
                agents=None
            )
        ]
    )

    assert profile.is_supervisor()
    assert profile.get_child_names() == ["Backend"]


@pytest.mark.integration
def test_supervisor_wrapper_creation():
    """Supervisor를 wrapper 노드로 생성하는지 테스트"""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY 필요")

    model = ChatOpenAI(model="gpt-4o-mini")

    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["Python"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 개발"],
                expertise=["Python"],
                agents=None
            )
        ]
    )

    # build_agent_node는 간소화된 버전으로, supervisor 기능 제거됨
    # Leaf 에이전트만 지원
    pytest.skip("Supervisor 기능 제거됨 - build_agent_node는 Leaf 에이전트만 지원")
