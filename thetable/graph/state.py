"""Meeting state definition"""
from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class AgentInfo(BaseModel):
    """Agent 기본 정보"""
    name: str
    role: str
    profile_key: str  # agent_profiles.yaml의 키


class MeetingState(TypedDict):
    """회의 상태"""

    # 대화 히스토리 (자동 누적)
    messages: Annotated[List[BaseMessage], add_messages]

    # Phase 관리
    current_phase: str  # "opening", "status_check", "issue_resolution", "closing"
    phase_history: List[str]  # Phase 전환 이력

    # Agent 관리
    agents: List[AgentInfo]
    next_speaker: Optional[str]  # 다음 발언자 이름
    current_task: Optional[str]  # Supervisor가 부여한 task

    # 발언 추적
    speaker_counts: Dict[str, int]
    pending_mentions: List[str]

    # Phase 제약
    phase_required_speakers: Dict[str, List[str]]  # Phase별 필수 발언자
    phase_goals: Dict[str, str]  # Phase별 목표

    # 메타데이터
    start_time: float
    phase_start_time: float
