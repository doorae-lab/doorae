"""RefillSpeakersNode 테스트"""

import pytest

from doorae.core.profile import AgentProfile
from doorae.graph.nodes.refill import RefillSpeakersNode
from doorae.graph.participant_registry import ParticipantRegistry
from doorae.graph.state import MeetingState


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

    @pytest.mark.asyncio
    async def test_filter_invalid_speakers(self):
        """비활성 에이전트 필터링 테스트"""
        # 활성 에이전트만 포함된 valid_speakers
        valid_speakers = {"Host", "PM", "TechLead"}
        node = RefillSpeakersNode(valid_speakers=valid_speakers)

        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[
                {
                    "title": "안건1",
                    "status": "in_progress",
                    # Designer, DevOps는 비활성 에이전트
                    "required_speakers": ["PM", "Designer", "DevOps", "TechLead"],
                }
            ],
            current_agenda_idx=0,
            speaker_counts={},
        )

        result = await node.execute(state)

        # 비활성 에이전트(Designer, DevOps)는 제외되고 활성 에이전트만 반환
        assert "Designer" not in result["pending_speakers"]
        assert "DevOps" not in result["pending_speakers"]
        assert all(speaker in valid_speakers for speaker in result["pending_speakers"])
        # PM과 TechLead 중 최대 2명
        assert len(result["pending_speakers"]) <= 2

    @pytest.mark.asyncio
    async def test_filter_all_invalid_speakers_delegates_to_host(self):
        """모든 required_speakers가 비활성이면 Host 위임"""
        valid_speakers = {"Host", "PM"}
        node = RefillSpeakersNode(valid_speakers=valid_speakers)

        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[
                {
                    "title": "안건1",
                    "status": "in_progress",
                    # 모두 비활성 에이전트
                    "required_speakers": ["Designer", "DevOps"],
                }
            ],
            current_agenda_idx=0,
            speaker_counts={},
            consecutive_host_delegations=0,
        )

        result = await node.execute(state)

        # 필터링 후 남은 게 없으므로 Host에 위임
        assert result["pending_speakers"] == ["Host"]
        assert result["consecutive_host_delegations"] == 1

    @pytest.mark.asyncio
    async def test_uses_registry_for_dynamic_valid_speakers(self):
        """registry 갱신이 valid_speakers에 동적으로 반영된다."""
        registry = ParticipantRegistry(
            {
                "Host": AgentProfile(
                    name="Host",
                    role="host",
                    responsibilities=["진행"],
                    expertise=["퍼실리테이션"],
                ),
                "Alice": AgentProfile(
                    name="Alice",
                    role="participant",
                    responsibilities=["참여"],
                    expertise=["일반"],
                    is_human=True,
                ),
            }
        )
        node = RefillSpeakersNode(registry=registry)

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
            speaker_counts={},
        )

        result = await node.execute(state)

        assert result["pending_speakers"] == ["Alice"]
