"""Host 중재 컨텍스트 생성 유틸리티.

주기적 Host 체크인 시 발언 통계, 반복 n-gram, 미발언자 정보를
Markdown 형식으로 생성하여 Host 프롬프트에 삽입한다.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Sequence

from langchain_core.messages import BaseMessage

# 불용어 (n-gram 필터링 — 한국어 조사, 접속사, 일반적 회의 표현)
_STOPWORDS: frozenset[str] = frozenset(
    {
        "그리고",
        "하지만",
        "그래서",
        "따라서",
        "이에",
        "대해",
        "의견",
        "부탁",
        "감사",
        "드립니다",
        "합니다",
        "입니다",
        "있습니다",
        "없습니다",
        "것입니다",
        "같습니다",
        "대한",
        "통해",
        "위해",
        "있는",
        "없는",
        "하는",
        "것을",
        "것이",
        "수도",
    }
)


def extract_repeated_ngrams(
    messages: Sequence[BaseMessage],
    n_range: tuple[int, int] = (2, 3),
    min_speakers: int = 2,
    top_k: int = 3,
) -> list[tuple[str, int]]:
    """메시지에서 여러 화자가 반복 사용한 n-gram 추출.

    Args:
        messages: 분석 대상 메시지 리스트 (현재 안건 구간만 전달).
        n_range: n-gram 범위 (min_n, max_n). 기본 (2, 3).
        min_speakers: 최소 화자 수. 기본 2.
        top_k: 반환할 최대 n-gram 수. 기본 3.

    Returns:
        [(phrase, count), ...] 빈도 내림차순, 최대 top_k 개.
    """
    if not messages:
        return []

    # ngram -> 총 빈도
    ngram_counts: Counter[str] = Counter()
    # ngram -> 화자 집합
    ngram_speakers: dict[str, set[str]] = defaultdict(set)

    min_n, max_n = n_range

    for msg in messages:
        speaker = getattr(msg, "name", None) or ""
        content = getattr(msg, "content", None) or ""
        tokens = content.split()

        if len(tokens) < min_n:
            continue

        for n in range(min_n, max_n + 1):
            for i in range(len(tokens) - n + 1):
                gram_tokens = tokens[i : i + n]
                # 불용어만으로 구성된 n-gram 또는 불용어를 포함한 n-gram 제외
                if any(tok in _STOPWORDS for tok in gram_tokens):
                    continue
                phrase = " ".join(gram_tokens)
                ngram_counts[phrase] += 1
                if speaker:
                    ngram_speakers[phrase].add(speaker)

    # min_speakers 이상의 화자가 사용한 n-gram만 필터
    filtered = [
        (phrase, count)
        for phrase, count in ngram_counts.items()
        if len(ngram_speakers.get(phrase, set())) >= min_speakers
    ]

    # 빈도 내림차순 정렬
    filtered.sort(key=lambda x: x[1], reverse=True)

    return filtered[:top_k]


def build_mediation_context(
    agenda_turn_count: int,
    agenda_speaker_counts: dict[str, int],
    agenda_max_turns: int,
    repeated_ngrams: list[tuple[str, int]],
    all_speaker_names: Sequence[str],
) -> str:
    """Host 프롬프트에 삽입할 중재 컨텍스트 Markdown 생성.

    Args:
        agenda_turn_count: 현재 안건에서 진행된 턴 수.
        agenda_speaker_counts: 현재 안건 구간의 화자별 발언 수.
        agenda_max_turns: 설정된 체크인 주기 (참고 정보).
        repeated_ngrams: extract_repeated_ngrams 반환값.
        all_speaker_names: 전체 참여자 이름 목록.

    Returns:
        Markdown 형식 문자열.
    """
    lines: list[str] = ["## 📊 토론 현황 분석", ""]

    # 발언 통계
    lines.append("### 발언 통계")
    lines.append("| 참여자 | 발언 횟수 |")
    lines.append("|--------|----------|")
    for name in all_speaker_names:
        count = agenda_speaker_counts.get(name, 0)
        lines.append(f"| {name} | {count} |")
    lines.append("")

    # 미발언자 감지
    silent = [
        name for name in all_speaker_names if agenda_speaker_counts.get(name, 0) == 0
    ]
    if silent:
        lines.append("### ⚠️ 미발언자")
        for name in silent:
            lines.append(f"- {name}")
        lines.append("")

    # 반복 키워드
    if repeated_ngrams:
        lines.append("### 🔄 반복 논점 감지")
        lines.append("다음 구문이 여러 참여자에 의해 반복되고 있습니다:")
        for idx, (phrase, count) in enumerate(repeated_ngrams, 1):
            lines.append(f"{idx}. \"{phrase}\" ({count}회)")
        lines.append("")
        lines.append(
            "💡 반복 논점이 감지되었습니다. "
            "합의가 형성되었다면 결론을 내리고, "
            "이견이 있다면 쟁점을 명확히 하여 논의를 전진시켜 주세요."
        )

    return "\n".join(lines)
