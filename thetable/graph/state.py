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


class MeetingState(MessagesState):
    """회의 상태"""

    # 안건 관리
    agendas: List[dict] = []  # Agenda 리스트 (dict로 저장)
    current_agenda_idx: int = 0

    # 발언자 큐
    pending_speakers: List[str] = []  # ["PM", "Designer", ...]

    # 발언 추적
    speaker_counts: Dict[str, int] = {}

    # Host 위임 추적 (무한루프 방지)
    consecutive_host_delegations: int = 0

    # 메타데이터
    start_time: float = 0.0
