"""Hierarchical 에이전트 팩토리

YAML 프로필에서 재귀적으로 에이전트 그래프 빌드
"""
from typing import Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from thetable.core.profile import AgentProfile
from thetable.graph.prompts import build_supervisor_prompt


def build_agent_graph(
    profile: AgentProfile,
    model: ChatOpenAI
) -> Any:
    """프로필에서 재귀적으로 에이전트 그래프 빌드

    Args:
        profile: 에이전트 프로필
        model: LLM 모델

    Returns:
        Leaf: create_react_agent (Pregel 객체)
        Supervisor: Callable wrapper function wrapping compiled supervisor graph
    """
    # Leaf 노드인 경우 (기존 로직)
    if not profile.is_supervisor():
        return create_react_agent(
            model=model,
            tools=[],
            prompt=_build_agent_prompt(profile),
            name=profile.name,
            version='v2'
        )

    # Supervisor 노드인 경우 (새로운 로직)
    # 1. 하위 에이전트 재귀 빌드
    child_agents = [
        build_agent_graph(child_profile, model)
        for child_profile in profile.agents
    ]

    # 2. 내부 supervisor 컴파일
    internal_supervisor = create_supervisor(
        agents=child_agents,
        model=model,
        supervisor_name=f"{profile.name}_internal",
        prompt=build_supervisor_prompt(profile, profile.get_child_names()),
        add_handoff_back_messages=True
    ).compile()

    # 3. Wrapper 함수 생성
    def supervisor_wrapper(state: dict) -> dict:
        return internal_supervisor.invoke(state)

    supervisor_wrapper.name = profile.name
    return supervisor_wrapper


def _build_agent_prompt(profile: AgentProfile) -> str:
    """프로필에서 에이전트 프롬프트 생성"""
    return f"""You are {profile.name}, a {profile.role}.

Responsibilities:
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

Expertise:
{chr(10).join(f'- {e}' for e in profile.expertise)}

Respond concisely and professionally in Korean."""





