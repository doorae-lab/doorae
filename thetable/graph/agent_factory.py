"""Flat 에이전트 팩토리

YAML 프로필에서 에이전트 그래프 빌드 (모든 에이전트가 leaf)
"""
from typing import Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from thetable.core.profile import AgentProfile


def build_agent_graph(
    profile: AgentProfile,
    model: ChatOpenAI
) -> Any:
    """프로필에서 에이전트 그래프 빌드

    Args:
        profile: 에이전트 프로필
        model: LLM 모델

    Returns:
        create_react_agent (Pregel 객체)
    """
    return create_react_agent(
        model=model,
        tools=[],
        prompt=_build_agent_prompt(profile),
        name=profile.name,
        version='v2'  # Use latest version to suppress deprecation warnings
    )


def _build_agent_prompt(profile: AgentProfile) -> str:
    """프로필에서 에이전트 프롬프트 생성"""
    return f"""You are {profile.name}, a {profile.role}.

Responsibilities:
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

Expertise:
{chr(10).join(f'- {e}' for e in profile.expertise)}

Respond concisely and professionally in Korean."""





