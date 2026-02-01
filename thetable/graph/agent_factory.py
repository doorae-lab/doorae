"""에이전트 팩토리

에이전트 노드 생성 (핸드오프 도구 제거, 간소화된 프롬프트)
"""
from typing import Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from thetable.core.profile import AgentProfile








def build_agent_node(
    profile: AgentProfile,
    model: ChatOpenAI,
    all_agent_names: list[str] = None
) -> Any:
    """에이전트 노드 빌드 (핸드오프 도구 없음, 간소화)

    Args:
        profile: 에이전트 프로필
        model: LLM 모델
        all_agent_names: 전체 참여자 목록

    Returns:
        create_react_agent 객체를 감싼 래퍼 함수
    """
    # 도구 없음 (또는 에이전트별 전용 도구만)
    tools = []

    agent_prompt = _build_agent_prompt(profile, all_agent_names)

    base_agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=agent_prompt,
        name=profile.name,
        version='v2'
    )
    
    # 메시지에 name 속성을 설정하는 래퍼 함수
    async def agent_with_name(state):
        result = await base_agent.ainvoke(state)
        
        # 생성된 메시지에 name 속성 추가
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "name") and not msg.name:
                    msg.name = profile.name
                elif not hasattr(msg, "name"):
                    msg.name = profile.name
        
        return result
    
    return agent_with_name


def _build_agent_prompt(
    profile: AgentProfile,
    participants: list[str] = None
) -> str:
    """프로필에서 에이전트 프롬프트 생성 (핸드오프 지침 제거)
    
    Args:
        profile: 에이전트 프로필
        participants: 참여자 목록
    """
    
    participants_section = ""
    if participants:
        others = [p for p in participants if p != profile.name]
        if others:
            participants_section = f"""

## 회의 참여자
다른 참여자: {', '.join(others)}

다른 참여자의 의견이 필요하면 자연스럽게 언급하세요.
예: "Designer님의 의견도 듣고 싶습니다"
"""

    return f"""당신은 {profile.name}, {profile.role}입니다.

## 책임
{chr(10).join(f'- {r}' for r in profile.responsibilities)}

## 전문 분야
{chr(10).join(f'- {e}' for e in profile.expertise)}
{participants_section}
간결하고 전문적으로 한국어로 응답하세요."""





