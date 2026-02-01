"""에이전트 팩토리

단순 LLM 호출 기반 에이전트 노드 생성
"""
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage

from thetable.core.profile import AgentProfile








def build_agent_node(
    profile: AgentProfile,
    model: ChatOpenAI,
    all_agent_names: list[str] = None,
    all_profiles: dict = None
) -> Any:
    """에이전트 노드 빌드 (단순 LLM 호출)

    Args:
        profile: 에이전트 프로필
        model: LLM 모델
        all_agent_names: 전체 참여자 목록
        all_profiles: 전체 프로필 딕셔너리 (is_human 확인용)

    Returns:
        단순 LLM 호출 래퍼 함수
    """
    agent_prompt = _build_agent_prompt(profile, all_agent_names, all_profiles)

    async def agent_node(state):
        """단순 LLM 호출로 응답 생성"""
        from langchain_core.messages import HumanMessage
        
        messages = state.get("messages", [])
        
        # 대화 기록을 명확한 포맷으로 변환
        # (name 속성을 content에 포함시켜 모델이 문맥을 이해하도록)
        formatted_messages = []
        for msg in messages:
            content = getattr(msg, 'content', '') or ''
            if not content.strip():
                continue
            
            name = getattr(msg, 'name', None)
            msg_type = type(msg).__name__
            
            if msg_type == 'HumanMessage':
                # 사용자 메시지는 그대로
                formatted_messages.append(HumanMessage(content=f"[회의 시작 요청]\n{content}"))
            elif msg_type == 'AIMessage' and name:
                # AI 메시지는 발언자 이름을 포함
                formatted_messages.append(HumanMessage(content=f"[{name}의 발언]\n{content}"))
        
        # 현재 발언 요청 추가
        formatted_messages.append(HumanMessage(
            content=f"이제 {profile.name}({profile.role})로서 위 대화에 이어 발언해 주세요. 한국어로 간결하게 응답하세요."
        ))
        
        # 시스템 메시지 + 포맷된 대화 기록
        system_msg = SystemMessage(content=agent_prompt)
        # 발언자 정보를 태그로 추가하여 스트리밍 시 식별 가능하도록
        response = await model.ainvoke(
            [system_msg] + formatted_messages,
            config={"tags": [f"speaker:{profile.name}"], "run_name": profile.name}
        )
        
        # name 속성 설정
        response.name = profile.name
        
        # 빈 응답 처리
        content = getattr(response, 'content', '') or ''
        if not content.strip():
            response = AIMessage(
                content=f"({profile.name}: 현재 추가 의견이 없습니다.)",
                name=profile.name
            )
        
        return {"messages": [response]}

    return agent_node


def _build_agent_prompt(
    profile: AgentProfile,
    participants: list[str] = None,
    all_profiles: dict = None
) -> str:
    """프로필에서 에이전트 프롬프트 생성 (핸드오프 지침 제거)
    
    Args:
        profile: 에이전트 프로필
        participants: 참여자 목록
        all_profiles: 전체 프로필 딕셔너리 (is_human 확인용)
    """
    
    participants_section = ""
    if participants:
        others = [p for p in participants if p != profile.name]
        if others:
            # is_human인 참여자에 * 표시
            formatted_participants = []
            for name in others:
                if all_profiles and name in all_profiles:
                    participant_profile = all_profiles[name]
                    if participant_profile.is_human:
                        formatted_participants.append(f"{name}*")
                    else:
                        formatted_participants.append(name)
                else:
                    formatted_participants.append(name)
            
            participants_section = f"""

## 회의 참여자
다른 참여자: {', '.join(formatted_participants)}
(* 표시는 실제 사용자입니다)

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





