"""계층적 에이전트 팩토리

langgraph-supervisor를 사용하여 YAML 프로필에서 재귀적으로 에이전트 그래프 빌드
"""
from typing import Union, Any
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

from thetable.core.profile import AgentProfile
from thetable.graph.prompts import build_supervisor_prompt


def build_agent_graph(
    profile: AgentProfile,
    model: ChatOpenAI
) -> Any:
    """프로필에서 재귀적으로 에이전트 그래프 빌드

    Args:
        profile: 에이전트 프로필 (계층 구조 포함)
        model: LLM 모델

    Returns:
        Leaf 노드: create_react_agent
        Supervisor 노드: wrapper function (내부에서 compiled subgraph 실행)
    """

    if not profile.is_supervisor():
        # Leaf 노드: ReAct 에이전트 생성
        return create_react_agent(
            model=model,
            tools=[],
            name=profile.name,
            prompt=_build_agent_prompt(profile)
        )

    # Supervisor 노드: 하위 에이전트들 재귀 빌드
    child_agents = []
    for child_profile in profile.agents:
        child_agent = build_agent_graph(child_profile, model)
        child_agents.append(child_agent)

    # 내부 supervisor 그래프 컴파일
    internal_supervisor = create_supervisor(
        agents=child_agents,
        model=model,
        supervisor_name=f"{profile.name}_internal",
        prompt=build_supervisor_prompt(profile, profile.get_child_names())
    ).compile()

    # 외부에는 일반 노드처럼 보이는 wrapper 함수 생성
    def supervisor_wrapper(state):
        """Wrapper that invokes internal supervisor subgraph"""
        result = internal_supervisor.invoke(state)
        return result

    # 함수에 name 속성 추가 (langgraph-supervisor가 이름으로 식별)
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



