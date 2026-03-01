"""Meeting state definition"""
from typing import List, Optional, Dict, Any
from langgraph.graph import MessagesState
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """Agent 기본 정보"""
    name: str
    role: str
    profile_key: str  # agent_profiles.yaml의 키


class Agenda(BaseModel):
    """회의 안건"""
    title: str
    description: str = ""  # 안건에 대한 상세 설명
    status: str = "pending"  # "pending", "in_progress", "completed", "deferred"
    required_speakers: List[str] = []  # 이 안건에서 발언해야 할 참여자

    # 추가 필드 (동적 안건 관리용)
    owner: Optional[str] = None  # 안건 담당자
    decision: Optional[str] = None  # 결정 사항
    time_limit: int = 300  # 초 단위 (5분 기본)
    start_time: Optional[float] = None  # Unix timestamp
    end_time: Optional[float] = None  # Unix timestamp


class MeetingState(MessagesState):
    """회의 상태"""

    # 안건 관리
    agendas: List[dict] = []  # Agenda 리스트 (dict로 저장)
    current_agenda_idx: int = 0
    pending_proposals: List[dict] = []  # 안건 후보 큐 (Host 승인 대기)

    # 발언자 큐
    pending_speakers: List[str] = []  # ["PM", "Designer", ...]

    # 발언 추적
    speaker_counts: Dict[str, int] = {}

    # Host 위임 추적 (무한루프 방지)
    consecutive_host_delegations: int = 0

    # 턴 관리 (무한루프 방지)
    turn_count: int = 0
    max_turns: int = 1000  # 최대 턴 수

    # 회의 종료 플래그
    meeting_ended: bool = False

    # 대화 요약
    summary: str = ""

    # 메타데이터
    start_time: float = 0.0
