"""doorae.graph.mediation 유틸리티 테스트."""

import pytest
from langchain_core.messages import AIMessage

from doorae.graph.mediation import (
    build_mediation_context,
    extract_repeated_ngrams,
)


class TestExtractRepeatedNgrams:
    """extract_repeated_ngrams 단위 테스트."""

    def test_empty_messages(self):
        """빈 메시지 리스트 → 빈 결과."""
        result = extract_repeated_ngrams([])
        assert result == []

    def test_single_speaker_filtered(self):
        """1명만 사용한 n-gram은 필터됨 (min_speakers=2)."""
        messages = [
            AIMessage(content="스프린트 주기를 논의합시다", name="PM"),
            AIMessage(content="스프린트 주기는 중요합니다", name="PM"),
        ]
        result = extract_repeated_ngrams(messages)
        assert result == []

    def test_repeated_across_speakers(self):
        """2명 이상이 사용한 n-gram이 반환된다."""
        messages = [
            AIMessage(content="스프린트 주기 2주로 제안합니다", name="PM"),
            AIMessage(content="스프린트 주기 2주 동의합니다", name="TechLead"),
        ]
        result = extract_repeated_ngrams(messages)
        phrases = [phrase for phrase, _ in result]
        assert "스프린트 주기" in phrases

    def test_stopwords_filtered(self):
        """불용어가 포함된 n-gram은 제외된다."""
        messages = [
            AIMessage(content="이에 대해 말씀드리면", name="PM"),
            AIMessage(content="이에 대해 생각해보면", name="TechLead"),
        ]
        result = extract_repeated_ngrams(messages)
        # "이에 대해"는 불용어 포함 → 필터
        assert result == []

    def test_top_k_limit(self):
        """상위 top_k개만 반환된다."""
        messages = [
            AIMessage(
                content="배포 전략 스프린트 주기 코드 리뷰 테스트 커버리지 기술 부채",
                name="PM",
            ),
            AIMessage(
                content="배포 전략 스프린트 주기 코드 리뷰 테스트 커버리지 기술 부채",
                name="TechLead",
            ),
        ]
        result = extract_repeated_ngrams(messages, top_k=2)
        assert len(result) <= 2

    def test_custom_n_range(self):
        """n_range 파라미터가 적용된다."""
        messages = [
            AIMessage(content="배포 전략 개선 방안 검토", name="PM"),
            AIMessage(content="배포 전략 개선 방안 논의", name="TechLead"),
        ]
        # 3-gram only
        result_3 = extract_repeated_ngrams(messages, n_range=(3, 3))
        phrases_3 = [phrase for phrase, _ in result_3]
        # "배포 전략 개선" should appear
        assert any("배포 전략 개선" in p for p in phrases_3)

    def test_returns_count(self):
        """반환된 튜플의 두 번째 요소는 빈도 수이다."""
        messages = [
            AIMessage(content="코드 리뷰 필요", name="PM"),
            AIMessage(content="코드 리뷰 중요", name="TechLead"),
            AIMessage(content="코드 리뷰 일정", name="QA"),
        ]
        result = extract_repeated_ngrams(messages)
        assert len(result) > 0
        phrase, count = result[0]
        assert phrase == "코드 리뷰"
        assert count == 3

    def test_sorted_by_count_descending(self):
        """빈도 내림차순으로 정렬된다."""
        messages = [
            AIMessage(content="코드 리뷰 배포 전략", name="PM"),
            AIMessage(content="코드 리뷰 배포 전략 코드 리뷰", name="TechLead"),
        ]
        result = extract_repeated_ngrams(messages)
        if len(result) >= 2:
            assert result[0][1] >= result[1][1]


class TestBuildMediationContext:
    """build_mediation_context 단위 테스트."""

    def test_includes_speaker_stats(self):
        """발언 횟수 테이블이 포함된다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5, "TechLead": 3},
            agenda_max_turns=10,
            repeated_ngrams=[],
            all_speaker_names=["PM", "TechLead"],
        )
        assert "| PM | 5 |" in context
        assert "| TechLead | 3 |" in context

    def test_includes_silent_participants(self):
        """미발언자가 표시된다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5, "TechLead": 3, "QA": 0},
            agenda_max_turns=10,
            repeated_ngrams=[],
            all_speaker_names=["PM", "TechLead", "QA"],
        )
        assert "미발언자" in context
        assert "- QA" in context

    def test_silent_includes_missing_speakers(self):
        """speaker_counts에 없는 참여자도 미발언자로 표시된다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5},
            agenda_max_turns=10,
            repeated_ngrams=[],
            all_speaker_names=["PM", "Designer"],
        )
        assert "- Designer" in context

    def test_includes_repeated_ngrams(self):
        """반복 키워드 섹션이 포함된다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5, "TechLead": 3},
            agenda_max_turns=10,
            repeated_ngrams=[("스프린트 주기", 7), ("2주 단위", 5)],
            all_speaker_names=["PM", "TechLead"],
        )
        assert "반복 논점 감지" in context
        assert '"스프린트 주기"' in context
        assert "7회" in context
        assert '"2주 단위"' in context

    def test_no_ngrams_section_when_empty(self):
        """반복 키워드가 없으면 해당 섹션이 생략된다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5},
            agenda_max_turns=10,
            repeated_ngrams=[],
            all_speaker_names=["PM"],
        )
        assert "반복 논점 감지" not in context

    def test_no_silent_section_when_all_spoke(self):
        """모두 발언한 경우 미발언자 섹션이 없다."""
        context = build_mediation_context(
            agenda_turn_count=10,
            agenda_speaker_counts={"PM": 5, "TechLead": 3},
            agenda_max_turns=10,
            repeated_ngrams=[],
            all_speaker_names=["PM", "TechLead"],
        )
        assert "미발언자" not in context
