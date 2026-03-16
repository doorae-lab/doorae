"""ProcessResponseNode - 에이전트 응답 처리"""

import re
import time
from typing import Dict, Any

from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from doorae.config import get_settings
from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.registry import register_node
from doorae.graph.participant_registry import ParticipantRegistry
from doorae.graph.state import MeetingState
from doorae.graph.constants import HOST_ROLE_NAME, HOST_END_MEETING_COMMAND


@register_node("process_response", category="utility")
class ProcessResponseNode(BaseNode):
    """에이전트 응답 처리 노드

    에이전트의 발언을 분석하여:
    - 멘션 추출 및 pending_speakers 업데이트
    - 안건 완료 감지 및 다음 안건으로 전환
    - 회의 종료 의도 감지
    - 발언 횟수 카운트

    Attributes:
        model: LLM 모델
        valid_speakers: 유효한 참여자 목록
    """

    node_type = NodeType.UTILITY
    requires_llm = True

    def __init__(
        self,
        model,
        valid_speakers: list[str] | None = None,
        registry: ParticipantRegistry | None = None,
    ):
        """초기화

        Args:
            model: LLM 모델 인스턴스
            valid_speakers: 유효한 참여자 이름 리스트
        """
        self.model = model
        self._valid_speakers = valid_speakers or []
        self._registry = registry

    @property
    def valid_speakers(self) -> list[str]:
        if self._registry is not None:
            return self._registry.all_names
        return list(self._valid_speakers)

    def _extract_at_mentions(self, content: str) -> list[str]:
        """`@Name` prefix 기반 멘션 추출."""
        if not content or not self.valid_speakers:
            return []

        ordered_speakers = sorted(self.valid_speakers, key=len, reverse=True)
        pattern = re.compile(
            r"@(" + "|".join(re.escape(speaker) for speaker in ordered_speakers) + r")"
        )

        mentions: list[str] = []
        for match in pattern.finditer(content):
            speaker = match.group(1)
            if speaker not in mentions:
                mentions.append(speaker)
        return mentions

    def _extract_natural_name_mentions(self, content: str) -> list[str]:
        """HumanMessage 호환용 자연어 이름 멘션 추출."""
        if not content or not self.valid_speakers:
            return []

        ordered_speakers = sorted(self.valid_speakers, key=len, reverse=True)
        pattern = re.compile(
            "|".join(re.escape(speaker) for speaker in ordered_speakers)
        )

        mentions: list[str] = []
        for match in pattern.finditer(content):
            speaker = match.group(0)
            if speaker not in mentions:
                mentions.append(speaker)
        return mentions

    def _looks_like_delegation_without_mentions(self, content: str) -> bool:
        """AI 응답이 멘션 없이 위임/호명을 시도하는지 추정."""
        if not content:
            return False

        request_cues = [
            "의견",
            "검토",
            "부탁",
            "생각",
            "말씀",
            "답변",
            "확인",
            "주시겠",
            "해주세요",
        ]
        if any(speaker in content for speaker in self.valid_speakers):
            return True
        return any(cue in content for cue in request_cues)

    async def _extract_mentions_with_llm(self, content: str) -> list[str]:
        """HumanMessage fallback용 제한된 LLM 멘션 추출."""
        settings = get_settings()
        prompt = f"""다음 발언에서 언급하거나 의견을 요청하는 참여자를 추출하세요.

발언: "{content}"

선택 가능한 참여자: {', '.join(self.valid_speakers)}

언급된 참여자 이름만 쉼표로 구분하여 출력 (없으면 "없음"):"""

        try:
            response_model = self.model.bind(max_tokens=settings.mention_extraction_max_tokens)
            response = await response_model.ainvoke(prompt)
            result = response.content.strip()

            if result == "없음":
                return []

            return [s.strip() for s in result.split(",") if s.strip() in self.valid_speakers]
        except Exception as e:
            logger.warning(
                f"⚠️ 멘션 추출 LLM 호출 실패 (발언: {content[:30]}...): {type(e).__name__}: {e}"
            )
            return []

    async def _extract_mentions(self, message: Any) -> list[str]:
        """메시지 유형별 멘션 추출."""
        content = getattr(message, "content", "") or ""
        at_mentions = self._extract_at_mentions(content)
        if at_mentions:
            return at_mentions

        if isinstance(message, AIMessage):
            if self._looks_like_delegation_without_mentions(content):
                logger.warning(
                    "⚠️ AI response attempted delegation without @mention "
                    f"(speaker={getattr(message, 'name', '')}, content={content[:80]!r})"
                )
            return []

        natural_mentions = self._extract_natural_name_mentions(content)
        if natural_mentions:
            return natural_mentions

        if isinstance(message, HumanMessage) and self._looks_like_delegation_without_mentions(content):
            return await self._extract_mentions_with_llm(content)

        return []

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

    async def _extract_decision(self, content: str, agenda_title: str) -> str:
        """Host의 안건 마무리 발언에서 결론을 한 줄로 추출."""
        settings = get_settings()
        prompt = (
            f"다음은 회의 진행자가 안건을 마무리하며 한 발언입니다.\n\n"
            f'안건: "{agenda_title}"\n'
            f'발언: "{content}"\n\n'
            f"이 발언에서 안건에 대한 결론/결정사항을 한 줄로 요약하세요.\n"
            f'결론이 없으면 "논의 계속"이라고 출력하세요.\n'
            f"요약만 출력하세요:"
        )

        try:
            response_model = self.model.bind(
                max_tokens=settings.mention_extraction_max_tokens
            )
            response = await response_model.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.warning(f"⚠️ 결론 추출 실패: {type(e).__name__}: {e}")
            return ""

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

    def _detect_meeting_end_command(self, content: str) -> bool:
        """마지막 비어있지 않은 줄이 종료 커맨드와 정확히 일치하는지 확인."""
        if not content:
            return False

        non_empty_lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not non_empty_lines:
            return False

        return non_empty_lines[-1] == HOST_END_MEETING_COMMAND

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
        mentions = await self._extract_mentions(last_msg)

        # 4. 새 멘션을 pending에 추가 (중복 제외)
        for m in mentions:
            if m not in new_pending and m != speaker_name:
                new_pending.append(m)

        # 5. Host 발언이면 안건 완료 체크
        new_idx = current_idx
        new_agendas = agendas.copy()
        meeting_ended = False

        if speaker_name == HOST_ROLE_NAME and self._detect_agenda_completion(content):
            if current_idx < len(new_agendas):
                decision = await self._extract_decision(
                    content, str(new_agendas[current_idx].get("title", ""))
                )
                new_agendas[current_idx]["status"] = "completed"
                new_agendas[current_idx]["end_time"] = time.time()
                if decision:
                    new_agendas[current_idx]["decision"] = decision
                new_idx = current_idx + 1
                # 다음 안건 시작 시간 설정
                if new_idx < len(new_agendas):
                    new_agendas[new_idx]["status"] = "in_progress"
                    new_agendas[new_idx]["start_time"] = time.time()
                new_pending = []  # 안건 변경 시 pending 초기화

        # 6. Host 회의 종료 발언 감지 (안건 상태 무관)
        if speaker_name == HOST_ROLE_NAME:
            if isinstance(last_msg, AIMessage):
                meeting_ended = self._detect_meeting_end_command(content)
            else:
                meeting_ended = (
                    self._detect_meeting_end_command(content)
                    or self._detect_meeting_end_keyword(content)
                )

        # 턴 카운트 증가
        turn_count = state.get("turn_count", 0) + 1

        # 7. 주기적 Host 체크인
        settings = get_settings()
        interval = settings.host_checkin_interval
        agenda_start = state.get("current_agenda_start_turn", 0)
        agenda_turns = turn_count - agenda_start

        if (
            interval > 0
            and agenda_turns > 0
            and agenda_turns % interval == 0
            and speaker_name != HOST_ROLE_NAME
            and HOST_ROLE_NAME not in new_pending
        ):
            new_pending.insert(0, HOST_ROLE_NAME)

        # 8. 안건 전환 시 current_agenda_start_turn 갱신
        new_agenda_start_turn = state.get("current_agenda_start_turn", 0)
        if new_idx != current_idx:
            new_agenda_start_turn = turn_count

        return {
            "pending_speakers": new_pending,
            "speaker_counts": new_counts,
            "current_agenda_idx": new_idx,
            "agendas": new_agendas,
            "consecutive_host_delegations": 0,  # 정상 진행 시 리셋
            "turn_count": turn_count,
            "meeting_ended": meeting_ended,
            "current_agenda_start_turn": new_agenda_start_turn,
        }
