"""안건 추출 및 관리 유틸리티"""

import json
from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from pydantic import BaseModel, Field


class AgendaExtractionResult(BaseModel):
    """안건 추출 결과"""
    items: List[dict] = Field(
        default_factory=list,
        description="업데이트된 안건 리스트 (dict 형태)"
    )
    changes_summary: Optional[str] = Field(
        default=None,
        description="변경사항 요약 (디버깅용)"
    )


async def extract_agenda_updates(
    llm: BaseChatModel,
    messages: List[BaseMessage],
    current_items: List[dict],
) -> AgendaExtractionResult:
    """
    최근 대화를 분석하여 안건 추가/수정/제거

    Args:
        llm: LLM 모델
        messages: 최근 대화 메시지 (마지막 10개 권장)
        current_items: 현재 안건 리스트 (dict 형태)

    Returns:
        AgendaExtractionResult: 업데이트된 안건 리스트
    """
    # 현재 안건 컨텍스트 생성
    current_agenda_text = ""
    if current_items:
        current_agenda_text = "**현재 안건 목록:**\n"
        for idx, item in enumerate(current_items, 1):
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "deferred": "⏸️"
            }.get(item.get("status", "pending"), "❓")
            owner_text = f" (담당: {item['owner']})" if item.get("owner") else ""
            decision_text = f" → \"{item['decision']}\"" if item.get("decision") else ""
            current_agenda_text += f"{idx}. {status_emoji} {item['title']}{owner_text}{decision_text}\n"
    else:
        current_agenda_text = "**현재 안건 목록:** (없음)\n"

    # 대화 컨텍스트 생성
    conversation_text = ""
    for msg in messages[-10:]:  # 최근 10개만
        role = getattr(msg, 'name', 'Unknown')
        content = getattr(msg, 'content', '')
        conversation_text += f"**{role}**: {content}\n\n"

    # 안건 추출 프롬프트
    system_prompt = f"""당신은 회의 안건을 추출하고 관리하는 AI입니다.

{current_agenda_text}

**최근 대화 내용:**
{conversation_text}

**안건 추출 규칙:**
1. 구체적인 논의 주제만 안건으로 등록 (일반 인사, 잡담은 제외)
2. 상태 변경은 대화에 명확한 근거가 있을 때만
3. 기존 안건은 절대 삭제하지 않음 (업데이트만 가능)
4. 제목은 한국어로 작성, 30자 이내
5. 담당자(owner)는 명시적으로 언급된 경우만 설정
6. 결정사항(decision)은 명확한 결론이 나왔을 때만 기록

**상태 종류:**
- pending: 아직 논의 안 됨
- in_progress: 현재 논의 중
- completed: 완료
- deferred: 보류/연기

**필수 필드:**
- title (str): 안건 제목
- description (str): 안건 설명 (선택)
- status (str): 상태 (기본값: "pending")
- required_speakers (list): 필수 발언자 (선택)
- owner (str): 담당자 (선택)
- decision (str): 결정사항 (선택)

대화 내용을 분석하여 안건 목록을 업데이트하세요. 변경사항이 없으면 기존 목록을 그대로 반환하세요."""

    try:
        # 1차 시도: 구조화된 출력
        structured_llm = llm.with_structured_output(AgendaExtractionResult)
        result = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content="위 대화를 분석하여 안건 목록을 업데이트해주세요.")
        ])
        return result

    except Exception as e:
        # 2차 시도: JSON 파싱
        try:
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt + "\n\nJSON 형식으로 응답하세요."),
                HumanMessage(content="위 대화를 분석하여 안건 목록을 업데이트해주세요.")
            ])

            # JSON 추출
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # AgendaExtractionResult로 변환
            return AgendaExtractionResult(
                items=data.get("items", []),
                changes_summary=data.get("changes_summary")
            )

        except Exception as inner_e:
            # 최종 fallback: 기존 안건 유지
            print(f"⚠️ 안건 추출 실패 (유지): {e}, {inner_e}")
            return AgendaExtractionResult(
                items=current_items,
                changes_summary=f"추출 실패, 기존 안건 유지: {str(e)}"
            )
