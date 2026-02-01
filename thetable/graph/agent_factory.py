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
    model: ChatOpenAI,
    all_agent_names: list[str] = None
) -> Any:
    """프로필에서 재귀적으로 에이전트 그래프 빌드

    Args:
        profile: 에이전트 프로필
        model: LLM 모델
        all_agent_names: 전체 참여자 목록 (다른 에이전트를 언급할 수 있도록)

    Returns:
        Leaf: create_react_agent (Pregel 객체)
        Supervisor: Callable wrapper function wrapping compiled supervisor graph
    """
    # Leaf 노드인 경우 (기존 로직)
    if not profile.is_supervisor():
        return create_react_agent(
            model=model,
            tools=[],
            prompt=_build_agent_prompt(profile, all_agent_names),
            name=profile.name,
            version='v2'
        )

    # Supervisor 노드인 경우 (새로운 로직)
    # 1. 하위 에이전트 재귀 빌드
    child_agents = [
        build_agent_graph(child_profile, model, all_agent_names)
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

    # 3. Wrapper class 생성 (invoke/ainvoke/__call__ 지원)
    class SupervisorWrapper:
        """Supervisor를 callable 노드로 감싸는 wrapper"""
        def __init__(self, supervisor, name):
            self._supervisor = supervisor
            self.name = name

        def __call__(self, state: dict, config: dict = None) -> dict:
            """Make instance callable (LangGraph v2 passes config)"""
            return self.invoke(state, config)

        def invoke(self, state: dict, config: dict = None) -> dict:
            if config:
                return self._supervisor.invoke(state, config)
            return self._supervisor.invoke(state)

        async def ainvoke(self, state: dict, config: dict = None) -> dict:
            if config:
                return await self._supervisor.ainvoke(state, config)
            return await self._supervisor.ainvoke(state)

    return SupervisorWrapper(internal_supervisor, profile.name)


def _build_agent_prompt(profile: AgentProfile, participants: list[str] = None) -> str:
    """프로필에서 에이전트 프롬프트 생성"""
    
    participants_section = ""
    if participants:
        others = [p for p in participants if p != profile.name]
        if others:
            participants_section = f"""

## Meeting Participants
Other participants: {', '.join(others)}

When you need input from others, mention them naturally:
- "TechLead님, 이 부분 기술 검토 부탁드립니다"
- "DevOps님 인프라 관점에서 의견 주세요"
- "Designer님 UX 측면은 어떨까요?"
"""

    return f"""You are {profile.name}, a {profile.role}.

## Responsibilities
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

## Expertise
{chr(10).join(f'- {e}' for e in profile.expertise)}
{participants_section}
Respond concisely and professionally in Korean.
When appropriate, mention other participants to request their input."""





