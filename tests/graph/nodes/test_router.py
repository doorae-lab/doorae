"""라우터 함수 테스트"""

import pytest
from langgraph.graph import END
from thetable.graph.nodes.router import condition_router
from thetable.graph.state import MeetingState


class TestConditionRouter:
    """condition_router 함수 테스트"""

    def test_route_to_first_pending_speaker(self):
        """pending_speakers의 첫 번째 참여자로 라우팅"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice", "Bob"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
        )

        result = condition_router(state)

        assert result == "alice"

    def test_route_to_refill_when_pending_empty(self):
        """pending_speakers가 비어있으면 refill_speakers로"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
        )

        result = condition_router(state)

        assert result == "refill_speakers"

    def test_route_to_end_when_meeting_ended(self):
        """meeting_ended 플래그가 True이면 END"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
            meeting_ended=True,
        )

        result = condition_router(state)

        assert result == END

    def test_route_to_end_when_max_turns_exceeded(self):
        """최대 턴 수 초과 시 END"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
            turn_count=30,
            max_turns=30,
        )

        result = condition_router(state)

        assert result == END

    def test_route_to_end_when_all_agendas_completed(self):
        """모든 안건 완료 시 END"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice"],
            agendas=[{"title": "안건1", "status": "completed"}],
            current_agenda_idx=1,  # 인덱스가 안건 수를 초과
        )

        result = condition_router(state)

        assert result == END

    def test_priority_meeting_ended_over_pending(self):
        """meeting_ended가 pending_speakers보다 우선"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice", "Bob"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
            meeting_ended=True,
        )

        result = condition_router(state)

        assert result == END

    def test_priority_max_turns_over_pending(self):
        """max_turns가 pending_speakers보다 우선"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
            turn_count=50,
            max_turns=30,
        )

        result = condition_router(state)

        assert result == END

    def test_lowercase_speaker_name(self):
        """참여자 이름이 소문자로 변환됨"""
        state = MeetingState(
            messages=[],
            pending_speakers=["Alice"],
            agendas=[{"title": "안건1", "status": "in_progress"}],
            current_agenda_idx=0,
        )

        result = condition_router(state)

        assert result == "alice"
        assert result != "Alice"

    def test_default_values(self):
        """기본값으로 작동"""
        state = MeetingState(
            messages=[],
            pending_speakers=[],
            agendas=[{"title": "안건1"}],
        )

        result = condition_router(state)

        assert result == "refill_speakers"
