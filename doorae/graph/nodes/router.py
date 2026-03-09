"""라우터 함수 - 워크플로우 분기 결정"""

from langgraph.graph import END
from doorae.graph.state import MeetingState


def condition_router(state: MeetingState) -> str:
    """pending_speakers 기반 라우팅

    LLM 없이 상태만으로 다음 노드를 결정합니다.

    Args:
        state: 현재 회의 상태

    Returns:
        다음 노드 이름 (참여자 이름 소문자 또는 'refill_speakers' 또는 END)

    라우팅 우선순위:
    1. meeting_ended 플래그 → END
    2. 최대 턴 수 초과 → END
    3. 모든 안건 완료 → END
    4. pending_speakers 존재 → 첫 번째 참여자
    5. pending_speakers 비어있음 → 'refill_speakers'
    """
    pending = state.get("pending_speakers", [])
    agendas = state.get("agendas", [])
    current_idx = state.get("current_agenda_idx", 0)
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 30)
    meeting_ended = state.get("meeting_ended", False)

    # 회의 종료 플래그 최우선 체크
    if meeting_ended:
        return END

    # 최대 턴 수 초과 체크 (무한루프 방지)
    if turn_count >= max_turns:
        return END

    # 모든 안건 완료 체크
    if current_idx >= len(agendas):
        return END

    # pending_speakers에 참여자가 있으면 첫 번째 참여자로 라우팅
    if pending:
        return pending[0].lower()

    # 빈 큐 → refill_speakers 노드로
    return "refill_speakers"
