"""대화 요약 관리"""
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langchain_openai import ChatOpenAI

from thetable.config import get_settings
from thetable.graph.state import MeetingState


async def summarize_conversation_node(
    state: MeetingState,
    model: ChatOpenAI
) -> Dict[str, Any]:
    """오래된 대화를 요약으로 압축

    동작:
    1. 메시지 개수 확인
    2. 임계값 초과 시 요약 생성
    3. 오래된 메시지 삭제
    4. 최근 N개 메시지만 유지

    Args:
        state: 현재 회의 상태

    Returns:
        업데이트된 summary와 삭제할 messages
    """
    settings = get_settings()
    messages = state.get("messages", [])
    current_summary = state.get("summary", "")

    # 메시지가 충분히 많을 때만 요약
    if len(messages) <= settings.max_messages_before_summary:
        return {}  # 변경 없음

    # 요약 프롬프트 생성
    if current_summary:
        summary_prompt = f"""## 기존 회의 요약
{current_summary}

## 새로운 대화 내용
위 대화 내용을 고려하여 기존 요약을 확장하세요.

요약 시 포함할 내용:
- 주요 논의 사항
- 결정 사항 및 담당자
- 각 참여자의 핵심 의견(개조식)
- 진행 중인 안건

간결하고 명확하게 한국어로 작성하세요."""
    else:
        summary_prompt = """지금까지의 회의 내용을 요약하세요.

요약 시 포함할 내용:
- 회의 주제 및 목적
- 주요 논의 사항
- 결정 사항 및 담당자
- 각 참여자의 핵심 의견(개조식)

간결하고 명확하게 한국어로 작성하세요."""

    # 요약 생성용 메시지 구성
    # (최근 메시지는 제외하여 중복 방지)
    messages_to_summarize = messages[:-settings.keep_recent_messages]

    formatted_messages = []
    for msg in messages_to_summarize:
        content = getattr(msg, 'content', '') or ''
        if not content.strip():
            continue
        name = getattr(msg, 'name', 'Unknown')
        formatted_messages.append(
            HumanMessage(content=f"[{name}]: {content}")
        )

    # 요약 프롬프트 추가
    formatted_messages.append(HumanMessage(content=summary_prompt))

    # 요약 생성 (전달받은 모델 사용)
    try:
        # max_tokens 제한을 위해 모델 바인딩
        summary_model = model.bind(max_tokens=settings.summary_max_tokens)
        response = await summary_model.ainvoke(formatted_messages)
        new_summary = response.content
    except Exception as e:
        # 요약 실패 시 기존 요약 유지
        print(f"요약 생성 실패: {e}")
        new_summary = current_summary

    # 오래된 메시지 삭제 (최근 N개만 유지)
    delete_messages = [
        RemoveMessage(id=m.id)
        for m in messages[:-settings.keep_recent_messages]
        if hasattr(m, 'id') and m.id
    ]

    return {
        "summary": new_summary,
        "messages": delete_messages
    }
