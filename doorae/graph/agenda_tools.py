"""안건 관리 Tool 생성 함수 (Closure 패턴)

모든 에이전트: propose_agenda
Host만: approve_agenda, reject_agenda
"""

from typing import List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class ProposeAgendaInput(BaseModel):
    title: str = Field(description="안건 제목 (30자 이내)")
    description: str = Field(default="", description="안건 설명")


class ApproveAgendaInput(BaseModel):
    proposal_index: int = Field(description="승인할 후보 안건의 인덱스 (0부터 시작)")


class RejectAgendaInput(BaseModel):
    proposal_index: int = Field(description="거절할 후보 안건의 인덱스 (0부터 시작)")
    reason: str = Field(default="", description="거절 사유")


def create_propose_tool(container: list, speaker_name: str) -> StructuredTool:
    """안건 제안 Tool 생성

    Args:
        container: 액션을 기록할 mutable list
        speaker_name: 제안하는 에이전트 이름

    Returns:
        propose_agenda StructuredTool
    """

    def propose_agenda(title: str, description: str = "") -> str:
        container.append({
            "action": "propose",
            "data": {
                "title": title,
                "description": description,
                "proposed_by": speaker_name,
                "status": "pending",
                "required_speakers": [],
            },
        })
        return f"안건 후보 등록 완료: '{title}' (Host 승인 대기 중)"

    return StructuredTool.from_function(
        func=propose_agenda,
        name="propose_agenda",
        description="새로운 안건을 후보로 제안합니다. Host가 승인하면 정식 안건이 됩니다.",
        args_schema=ProposeAgendaInput,
    )


def create_approve_tool(container: list, proposals: List[dict]) -> StructuredTool:
    """안건 후보 승인 Tool 생성 (Host 전용)

    Args:
        container: 액션을 기록할 mutable list
        proposals: 현재 pending_proposals 리스트 (읽기 전용 참조)

    Returns:
        approve_agenda StructuredTool
    """

    def approve_agenda(proposal_index: int) -> str:
        if proposal_index < 0 or proposal_index >= len(proposals):
            return f"오류: 유효하지 않은 인덱스 {proposal_index} (총 {len(proposals)}개 후보)"
        proposal = proposals[proposal_index]
        container.append({
            "action": "approve",
            "index": proposal_index,
            "data": proposal,
        })
        return f"안건 승인 완료: '{proposal.get('title', '')}'"

    return StructuredTool.from_function(
        func=approve_agenda,
        name="approve_agenda",
        description="대기 중인 안건 후보를 승인하여 정식 안건으로 등록합니다.",
        args_schema=ApproveAgendaInput,
    )


def create_reject_tool(container: list, proposals: List[dict]) -> StructuredTool:
    """안건 후보 거절 Tool 생성 (Host 전용)

    Args:
        container: 액션을 기록할 mutable list
        proposals: 현재 pending_proposals 리스트 (읽기 전용 참조)

    Returns:
        reject_agenda StructuredTool
    """

    def reject_agenda(proposal_index: int, reason: str = "") -> str:
        if proposal_index < 0 or proposal_index >= len(proposals):
            return f"오류: 유효하지 않은 인덱스 {proposal_index} (총 {len(proposals)}개 후보)"
        proposal = proposals[proposal_index]
        container.append({
            "action": "reject",
            "index": proposal_index,
            "reason": reason,
        })
        return f"안건 후보 거절: '{proposal.get('title', '')}'" + (f" (사유: {reason})" if reason else "")

    return StructuredTool.from_function(
        func=reject_agenda,
        name="reject_agenda",
        description="대기 중인 안건 후보를 거절합니다.",
        args_schema=RejectAgendaInput,
    )
