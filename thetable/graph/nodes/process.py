"""ProcessResponseNode - 에이전트 응답 처리"""

import time
import logging
from typing import Dict, Any
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.nodes.registry import register_node
# utils import 제거 - 함수들을 private 메서드로 이동
from thetable.graph.state import MeetingState

logger = logging.getLogger(__name__)


@register_node("process_response", category="utility")
class ProcessResponseNode(BaseNode):
    """에이전트 응답 처리 노드

    에이전트의 발언을 분석하여:
    - 멘션 추출 및 pending_speakers 업데이트
    - 안건 완료 감지 및 다음 안건으로 전환
    - 회의 종료 의도 감지
    - 발언 횟수 카운트
    - 안건 동적 업데이트

    Attributes:
        model: LLM 모델
        valid_speakers: 유효한 참여자 목록
    """

    node_type = NodeType.UTILITY
    requires_llm = True

    def __init__(self, model, valid_speakers: list[str]):
        """초기화

        Args:
            model: LLM 모델 인스턴스
            valid_speakers: 유효한 참여자 이름 리스트
        """
        self.model = model
        self.valid_speakers = valid_speakers

    async def _extract_mentions(self, content: str) -> list[str]:
        """LLM 기반 멘션 추출

        Args:
            content: 발언 내용

        Returns:
            언급된 참여자 이름 리스트
        """
        prompt = f"""다음 발언에서 언급하거나 의견을 요청하는 참여자를 추출하세요.

발언: "{content}"

선택 가능한 참여자: {', '.join(self.valid_speakers)}

언급된 참여자 이름만 쉼표로 구분하여 출력 (없으면 "없음"):"""

        response = await self.model.ainvoke(prompt)
        result = response.content.strip()

        if result == "없음":
            return []

        return [s.strip() for s in result.split(",") if s.strip() in self.valid_speakers]

    def _detect_agenda_completion(self, content: str) -> bool:
        """Host 발언에서 안건 완료 키워드 감지

        Args:
            content: 발언 내용

        Returns:
            안건 완료 키워드가 포함되어 있으면 True
        """
        completion_keywords = [
            "다음 안건",
            "다음으로",
            "넘어가",
            "마무리",
            "정리하면",
            "결론",
            "이 안건은 여기까지",
        ]
        return any(kw in content for kw in completion_keywords)

    def _detect_meeting_end_keyword(self, content: str) -> bool:
        """Host 발언에서 회의 종료 키워드 감지

        Args:
            content: 발언 내용

        Returns:
            회의 종료 키워드가 포함되어 있으면 True
        """
        end_keywords = [
            "회의를 마치겠습니다",
            "회의를 종료",
            "이상으로 마치겠습니다",
            "오늘 회의는 여기까지",
            "수고하셨습니다",
            "회의 종료",
        ]
        return any(kw in content for kw in end_keywords)

    async def _detect_meeting_end_llm(self, content: str) -> bool:
        """LLM으로 회의 종료 의도 분석

        키워드 미감지 시 fallback으로 사용됩니다.

        Args:
            content: 발언 내용

        Returns:
            회의 종료 의도가 감지되면 True
        """
        prompt = f"""다음 Host의 발언이 회의를 종료하려는 의도인지 판단하세요.

발언: "{content}"

회의 종료 의도가 명확하면 "예", 아니면 "아니오"로만 답하세요:"""

        response = await self.model.ainvoke(prompt)
        result = response.content.strip()

        return result == "예"

    def _merge_llm_agendas(
        self, agenda_result, existing_agendas: list[dict]
    ) -> list[dict] | None:
        """LLM 추출 안건과 기존 안건 병합

        Args:
            agenda_result: extract_agenda_updates 반환값
            existing_agendas: 기존 안건 리스트

        Returns:
            병합된 안건 리스트 또는 None (업데이트 불가 시)
        """
        if agenda_result is None:
            logger.warning("안건 추출 결과가 None, 기존 안건 유지")
            return None

        new_agendas = agenda_result.items_as_dicts()
        if not new_agendas:
            logger.warning("안건 추출 결과가 비어있어 기존 안건 유지")
            return None

        for i, new_agenda in enumerate(new_agendas):
            if i >= len(existing_agendas):
                break
            # 기존 안건의 값이 있고 새 안건에 없는 필드만 복원
            defaults = {
                k: v
                for k, v in existing_agendas[i].items()
                if v and not new_agenda.get(k)
            }
            new_agenda.update(defaults)

        return new_agendas

    def _ensure_agenda_timestamps(self, agendas: list[dict]) -> None:
        """안건 상태에 맞는 타임스탬프 보장

        Args:
            agendas: 타임스탬프를 확인할 안건 리스트 (in-place 수정)
        """
        now = time.time()
        for agenda in agendas:
            if agenda["status"] == "in_progress" and not agenda.get("start_time"):
                agenda["start_time"] = now
            if agenda["status"] in ("completed", "deferred") and not agenda.get(
                "end_time"
            ):
                agenda["end_time"] = now

    async def execute(self, state: MeetingState) -> Dict[str, Any]:
        """에이전트 응답 처리

        Args:
            state: 현재 회의 상태

        Returns:
            상태 업데이트를 위한 딕셔너리
        """
        messages = state.get("messages", [])
        pending = state.get("pending_speakers", [])
        speaker_counts = state.get("speaker_counts", {})
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)

        if not messages:
            return {}

        last_msg = messages[-1]
        speaker_name = getattr(last_msg, "name", "")
        content = getattr(last_msg, "content", "")

        # 1. 현재 발언자를 pending에서 제거
        new_pending = [s for s in pending if s != speaker_name]

        # 2. speaker_counts 업데이트
        new_counts = speaker_counts.copy()
        new_counts[speaker_name] = new_counts.get(speaker_name, 0) + 1

        # 3. 멘션 추출 (LLM 기반)
        mentions = await self._extract_mentions(content)

        # 4. 새 멘션을 pending에 추가 (중복 제외)
        for m in mentions:
            if m not in new_pending and m != speaker_name:
                new_pending.append(m)

        # 5. Host 발언이면 안건 완료 체크
        new_idx = current_idx
        new_agendas = agendas.copy()
        meeting_ended = False

        if speaker_name == "Host" and self._detect_agenda_completion(content):
            if current_idx < len(new_agendas):
                new_agendas[current_idx]["status"] = "completed"
                new_agendas[current_idx]["end_time"] = time.time()
                new_idx = current_idx + 1
                # 다음 안건 시작 시간 설정
                if new_idx < len(new_agendas):
                    new_agendas[new_idx]["status"] = "in_progress"
                    new_agendas[new_idx]["start_time"] = time.time()
                new_pending = []  # 안건 변경 시 pending 초기화

        # 6. Host 회의 종료 발언 감지 (안건 상태 무관)
        if speaker_name == "Host":
            # 1단계: 키워드 감지 (최우선, 안건 상태 무관)
            if self._detect_meeting_end_keyword(content):
                meeting_ended = True

            # 2단계: LLM 분석 (키워드 미감지 + 안건 대부분 완료)
            elif len(new_agendas) > 0:
                completed_count = sum(
                    1
                    for a in new_agendas
                    if a["status"] in ["completed", "deferred"]
                )
                completion_rate = completed_count / len(new_agendas)

                # 80% 이상 완료 시에만 LLM 분석 (토큰 절약)
                if completion_rate >= 0.8:
                    meeting_ended = await self._detect_meeting_end_llm(content)

        # 턴 카운트 증가
        turn_count = state.get("turn_count", 0) + 1

        # 7. 안건 동적 업데이트 (매 발언마다)
        from thetable.graph.agenda_manager import extract_agenda_updates

        try:
            # 최근 10개 메시지만 분석 (토큰 절약)
            recent_messages = messages[-10:] if len(messages) > 10 else messages

            agenda_result = await extract_agenda_updates(
                llm=self.model,
                messages=recent_messages,
                current_items=new_agendas,
            )

            # LLM 안건과 기존 안건 병합 (depth 개선)
            merged_agendas = self._merge_llm_agendas(agenda_result, new_agendas)
            if merged_agendas:
                new_agendas = merged_agendas
                # 타임스탬프 보장 (PR #75, #81)
                self._ensure_agenda_timestamps(new_agendas)

        except Exception as e:
            # 안건 업데이트 실패 시 기존 안건 유지
            logger.warning(f"⚠️ 안건 업데이트 실패: {e}")

        return {
            "pending_speakers": new_pending,
            "speaker_counts": new_counts,
            "current_agenda_idx": new_idx,
            "agendas": new_agendas,
            "consecutive_host_delegations": 0,  # 정상 진행 시 리셋
            "turn_count": turn_count,
            "meeting_ended": meeting_ended,
        }
