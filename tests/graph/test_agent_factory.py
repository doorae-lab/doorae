"""Tests for agent factory"""
import pytest
from unittest.mock import Mock, MagicMock
from langchain_openai import ChatOpenAI

from thetable.core.profile import AgentProfile
from thetable.graph.agent_factory import (
    build_agent_graph,
    _build_agent_prompt,
    _build_supervisor_prompt
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


def test_build_supervisor_prompt():
    """슈퍼바이저 프롬프트 생성 테스트"""
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["시스템 설계"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 설계"],
                expertise=["Python"]
            )
        ]
    )
    
    prompt = _build_supervisor_prompt(profile)
    
    assert "TechLead" in prompt
    assert "Backend" in prompt
    assert "기술 의사결정" in prompt


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


def test_supervisor_agent_creation(mock_model):
    """슈퍼바이저 에이전트 생성 테스트"""
    profile = AgentProfile(
        name="TechLead",
        role="tech_lead",
        responsibilities=["기술 의사결정"],
        expertise=["시스템 설계"],
        agents=[
            AgentProfile(
                name="Backend",
                role="backend_engineer",
                responsibilities=["API 설계"],
                expertise=["Python"]
            )
        ]
    )
    
    assert profile.is_supervisor()
    assert len(profile.get_child_names()) == 1
    assert "Backend" in profile.get_child_names()
