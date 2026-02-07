"""RefillSpeakersNode 테스트"""

import pytest
from thetable.graph.nodes.refill import RefillSpeakersNode
from thetable.graph.state import MeetingState


class TestRefillSpeakersNode:
    """RefillSpeakersNode 클래스 테스트"""

    @pytest.fixture
    def node(self):
        """테스트용 노드 인스턴스"""
        return RefillSpeakersNode()

    @pytest.mark.asyncio
    async def test_refill_with_remaining_speakers(self, node):
        """남은 required_speakers로 채우기"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[
                {
                    "title": "안건1",
                    "status": "in_progress",
                    "required_speakers": ["Alice", "Bob", "Charlie"],
                }
            ],
            current_agenda_idx=0,
            speaker_counts={"Alice": 1},
        )

        result = await node.execute(state)

        assert "Bob" in result["pending_speakers"]
        assert "Charlie" in result["pending_speakers"]
        assert len(result["pending_speakers"]) <= 2  # 최대 2명

    @pytest.mark.asyncio
    async def test_delegate_to_host_when_no_remaining(self, node):
        """required_speakers 모두 발언했으면 Host 위임"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[
                {
                    "title": "안건1",
                    "status": "in_progress",
                    "required_speakers": ["Alice", "Bob"],
                }
            ],
            current_agenda_idx=0,
            speaker_counts={"Alice": 1, "Bob": 1},
            consecutive_host_delegations=0,
        )

        result = await node.execute(state)

        assert result["pending_speakers"] == ["Host"]
        assert result["consecutive_host_delegations"] == 1

    @pytest.mark.asyncio
    async def test_force_host_after_consecutive_delegations(self, node):
        """연속 3회 Host 위임 시 강제 마무리"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[
                {
                    "title": "안건1",
                    "status": "in_progress",
                    "required_speakers": ["Alice"],
                }
            ],
            current_agenda_idx=0,
            speaker_counts={"Alice": 1},
            consecutive_host_delegations=3,
        )

        result = await node.execute(state)

        assert result["pending_speakers"] == ["Host"]
        assert result["consecutive_host_delegations"] == 0  # 리셋

    @pytest.mark.asyncio
    async def test_empty_when_all_agendas_completed(self, node):
        """모든 안건 완료 시 빈 리스트 반환"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[{"title": "안건1", "status": "completed"}],
            current_agenda_idx=1,  # 인덱스가 안건 수를 초과
            speaker_counts={},
        )

        result = await node.execute(state)

        assert result["pending_speakers"] == []
