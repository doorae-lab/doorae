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
        Supervisor 노드: create_supervisor().compile()
    """
    
    if not profile.is_supervisor():
        # Leaf 노드: ReAct 에이전트 생성
        return create_react_agent(
            model=model,
            tools=[],  # 프로필 기반 도구 추가 가능
            name=profile.name,
            prompt=_build_agent_prompt(profile)
        )
    
    # Supervisor 노드: 하위 에이전트들 재귀 빌드
    child_agents = []
    for child_profile in profile.agents:
        child_agent = build_agent_graph(child_profile, model)
        child_agents.append(child_agent)
    
    # 하위 에이전트들을 관리하는 supervisor 생성
    supervisor = create_supervisor(
        agents=child_agents,
        model=model,
        supervisor_name=profile.name,
        prompt=build_supervisor_prompt(profile, profile.get_child_names())
    )
    
    # 팀을 하나의 노드로 컴파일 (이름 일관성을 위해 _team 접미사 제거)
    return supervisor.compile(name=profile.name)


def _build_agent_prompt(profile: AgentProfile) -> str:
    """프로필에서 에이전트 프롬프트 생성"""
    return f"""You are {profile.name}, a {profile.role}.

Responsibilities:
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

Expertise:
{chr(10).join(f'- {e}' for e in profile.expertise)}

Respond concisely and professionally in Korean."""



