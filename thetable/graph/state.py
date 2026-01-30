"""Meeting state definition"""
from typing import List, Optional, Dict, Any
from langgraph.graph import MessagesState
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """Agent 기본 정보"""
    name: str
    role: str
    profile_key: str  # agent_profiles.yaml의 키


class MeetingState(MessagesState):
    """회의 상태 (MessagesState 상속 - langgraph-supervisor 호환)"""

    # Supervisor 제어
    remaining_steps: int = 10  # langgraph-supervisor 필수 필드: 남은 실행 단계 수

    # Phase 관리
    current_phase: str = "opening"  # "opening", "status_check", "issue_resolution", "closing"
    phase_history: List[str] = []  # Phase 전환 이력

    # Agent 관리
    agents: List[dict] = []  # AgentInfo 대신 dict 사용 (TypedDict 호환)
    next_speaker: Optional[str] = None  # 다음 발언자 이름
    current_task: Optional[str] = None  # Supervisor가 부여한 task

    # 발언 추적
    speaker_counts: Dict[str, int] = {}
    pending_mentions: List[str] = []

    # Phase 제약
    phase_required_speakers: Dict[str, List[str]] = {}  # Phase별 필수 발언자
    phase_goals: Dict[str, str] = {}  # Phase별 목표

    # 메타데이터
    start_time: float = 0.0
    phase_start_time: float = 0.0
