"""RefillSpeakersNode - pending_speakers 채우기"""

from typing import Dict, Any
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.nodes.registry import register_node
# utils import 제거 - 함수를 private 메서드로 이동
from thetable.graph.state import MeetingState
from thetable.graph.constants import HOST_ROLE_NAME


@register_node("refill_speakers", category="utility")
class RefillSpeakersNode(BaseNode):
    """pending_speakers 비었을 때 채우기 노드

    안건의 required_speakers 중 아직 발언하지 않은 참여자를 찾아
    pending_speakers에 추가합니다. 모든 required_speakers가 발언했다면
    Host에게 위임합니다.

    Attributes:
        model: LLM 모델 (현재 사용하지 않음, 향후 확장용)
    """

    node_type = NodeType.UTILITY

    def __init__(self, model=None):
        """초기화

        Args:
            model: LLM 모델 인스턴스 (향후 확장용, 현재는 사용 안 함)
        """
        self.model = model

    def _get_remaining_speakers(
        self, required_speakers: list[str], already_spoken: set
    ) -> list[str]:
        """안건의 required_speakers 중 아직 발언하지 않은 참여자 반환

        Args:
            required_speakers: 안건에서 요구하는 참여자 목록
            already_spoken: 이미 발언한 참여자 집합

        Returns:
            아직 발언하지 않은 참여자 리스트
        """
        return [s for s in required_speakers if s not in already_spoken]

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """pending_speakers 채우기

        Args:
            state: 현재 회의 상태

        Returns:
            상태 업데이트를 위한 딕셔너리
        """
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)
        speaker_counts = state.get("speaker_counts", {})
        consecutive = state.get("consecutive_host_delegations", 0)

        if current_idx >= len(agendas):
            return {"pending_speakers": []}  # 모든 안건 완료

        current_agenda = agendas[current_idx]
        required = current_agenda.get("required_speakers", [])

        # 1차: 안건의 required_speakers 중 미발언자
        already_spoken = set(speaker_counts.keys())
        remaining = self._get_remaining_speakers(required, already_spoken)

        if remaining:
            return {
                "pending_speakers": remaining[:2],  # 최대 2명씩
                "consecutive_host_delegations": 0,
            }

        # 2차: Host 위임 (무한루프 방지)
        if consecutive >= 3:
            # 강제로 Host가 마무리하도록
            return {
                "pending_speakers": [HOST_ROLE_NAME],
                "consecutive_host_delegations": 0,
            }

        return {
            "pending_speakers": [HOST_ROLE_NAME],
            "consecutive_host_delegations": consecutive + 1,
        }
