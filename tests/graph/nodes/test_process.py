"""ProcessResponseNode 테스트"""

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from doorae.graph.constants import HOST_END_MEETING_COMMAND
from doorae.graph.nodes.process import ProcessResponseNode, NodeType
from doorae.graph.participant_registry import ParticipantRegistry
from doorae.core.profile import AgentProfile


class TestProcessResponseNode:
    """ProcessResponseNode 클래스 테스트"""

    def test_node_type(self):
        """노드 타입이 UTILITY인지 확인"""
        assert ProcessResponseNode.node_type == NodeType.UTILITY

    def test_requires_llm(self):
        """LLM이 필요한 노드인지 확인"""
        assert ProcessResponseNode.requires_llm is True

    def test_initialization(self):
        """초기화 테스트"""
        from unittest.mock import MagicMock

        mock_model = MagicMock()
        valid_speakers = ["Host", "Alice", "Bob"]

        node = ProcessResponseNode(model=mock_model, valid_speakers=valid_speakers)

        assert node.model is mock_model
        assert node.valid_speakers == valid_speakers

    def test_no_extract_agenda_updates(self):
        """extract_agenda_updates가 ProcessResponseNode에서 호출되지 않는지 확인"""
        src = inspect.getsource(ProcessResponseNode)
        assert "extract_agenda_updates" not in src

    def test_no_merge_llm_agendas(self):
        """_merge_llm_agendas 메서드가 존재하지 않는지 확인"""
        assert not hasattr(ProcessResponseNode, "_merge_llm_agendas")

    def test_no_ensure_agenda_timestamps(self):
        """_ensure_agenda_timestamps 메서드가 존재하지 않는지 확인"""
        assert not hasattr(ProcessResponseNode, "_ensure_agenda_timestamps")

    def test_keyword_agenda_completion_detection(self):
        """키워드 기반 안건 완료 감지가 여전히 동작하는지 확인"""
        from unittest.mock import MagicMock

        node = ProcessResponseNode(model=MagicMock(), valid_speakers=["Host"])

        assert node._detect_agenda_completion("다음 안건으로 넘어가겠습니다") is True
        assert node._detect_agenda_completion("마무리하겠습니다") is True
        assert node._detect_agenda_completion("안녕하세요") is False

    def test_keyword_meeting_end_detection(self):
        """키워드 기반 회의 종료 감지가 여전히 동작하는지 확인"""
        node = ProcessResponseNode(model=MagicMock(), valid_speakers=["Host"])

        assert node._detect_meeting_end_keyword("회의를 마치겠습니다") is True
        assert node._detect_meeting_end_keyword("수고하셨습니다") is True
        assert node._detect_meeting_end_keyword("다음 안건으로 이동합니다") is False

    @pytest.mark.asyncio
    async def test_extract_mentions_from_ai_message_uses_at_prefix(self, monkeypatch):
        warn = MagicMock()
        monkeypatch.setattr("doorae.graph.nodes.process.logger.warning", warn)

        model = MagicMock()
        model.ainvoke = AsyncMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM", "TechLead"])

        mentions = await node._extract_mentions(
            AIMessage(content="@PM님 의견 부탁드립니다. @TechLead에게도 검토 부탁드립니다.", name="Host")
        )

        assert mentions == ["PM", "TechLead"]
        model.ainvoke.assert_not_called()
        warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_mentions_from_ai_message_has_no_fallback(self, monkeypatch):
        warn = MagicMock()
        monkeypatch.setattr("doorae.graph.nodes.process.logger.warning", warn)

        model = MagicMock()
        model.ainvoke = AsyncMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM", "TechLead"])

        mentions = await node._extract_mentions(
            AIMessage(content="PM님 의견 부탁드립니다.", name="Host")
        )

        assert mentions == []
        model.ainvoke.assert_not_called()
        warn.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_mentions_prefers_longer_names_first(self, monkeypatch):
        warn = MagicMock()
        monkeypatch.setattr("doorae.graph.nodes.process.logger.warning", warn)

        model = MagicMock()
        model.ainvoke = AsyncMock()
        node = ProcessResponseNode(model=model, valid_speakers=["PM", "PMO"])

        mentions = await node._extract_mentions(
            AIMessage(content="@PMO님 확인 부탁드립니다.", name="Host")
        )

        assert mentions == ["PMO"]
        model.ainvoke.assert_not_called()
        warn.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_mentions_from_human_message_supports_natural_name_without_llm(self):
        model = MagicMock()
        model.ainvoke = AsyncMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM", "TechLead"])

        mentions = await node._extract_mentions(
            HumanMessage(content="PM님 의견 부탁드립니다.", name="chulsoo")
        )

        assert mentions == ["PM"]
        model.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_mentions_from_human_message_uses_limited_llm_fallback(self, monkeypatch):
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(return_value=MagicMock(content="PM"))

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM", "TechLead"])

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(mention_extraction_max_tokens=64, host_checkin_interval=10),
        )

        mentions = await node._extract_mentions(
            HumanMessage(content="누가 답변하면 좋을까요? 의견 부탁드립니다.", name="chulsoo")
        )

        assert mentions == ["PM"]
        model.bind.assert_called_once_with(max_tokens=64)
        response_model.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extract_mentions_reads_registry_dynamically(self):
        registry = ParticipantRegistry(
            {
                "Host": AgentProfile(
                    name="Host",
                    role="host",
                    responsibilities=["진행"],
                    expertise=["퍼실리테이션"],
                ),
                "PM": AgentProfile(
                    name="PM",
                    role="participant",
                    responsibilities=["참여"],
                    expertise=["일반"],
                ),
            }
        )
        node = ProcessResponseNode(model=MagicMock(), registry=registry)
        registry.add(
            AgentProfile(
                name="TechLead",
                role="participant",
                responsibilities=["참여"],
                expertise=["일반"],
            )
        )

        mentions = await node._extract_mentions(
            AIMessage(content="@TechLead 의견 부탁드립니다.", name="Host")
        )

        assert mentions == ["TechLead"]

    def test_process_response_node_has_no_meeting_end_llm_fallback(self):
        """회의 종료 LLM fallback이 제거되었는지 확인"""
        assert not hasattr(ProcessResponseNode, "_detect_meeting_end_llm")

    def test_detect_meeting_end_command_matches_exact_last_non_empty_line(self):
        """종료 커맨드는 마지막 비어있지 않은 줄과 정확히 일치해야 함"""
        node = ProcessResponseNode(model=MagicMock(), valid_speakers=["Host"])

        assert (
            node._detect_meeting_end_command(
                f"오늘 논의는 여기까지 하겠습니다.\n{HOST_END_MEETING_COMMAND}"
            )
            is True
        )
        assert (
            node._detect_meeting_end_command(
                f"오늘 논의는 여기까지 하겠습니다.\n{HOST_END_MEETING_COMMAND}\n"
            )
            is True
        )
        assert (
            node._detect_meeting_end_command(
                f"{HOST_END_MEETING_COMMAND} 감사합니다."
            )
            is False
        )
        assert (
            node._detect_meeting_end_command(
                f"오늘 논의는 여기까지 하겠습니다. {HOST_END_MEETING_COMMAND}"
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_execute_routes_ai_mentions_into_pending_queue(self):
        node = ProcessResponseNode(model=MagicMock(), valid_speakers=["Host", "PM", "TechLead"])
        state = {
            "messages": [AIMessage(content="@PM님 의견 부탁드립니다.", name="Host")],
            "agendas": [{"title": "Test", "status": "in_progress", "required_speakers": ["Host", "PM"]}],
            "current_agenda_idx": 0,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 0,
        }

        result = await node.execute(state)

        assert result["pending_speakers"] == ["PM"]
        assert result["speaker_counts"] == {"Host": 1}

    @pytest.mark.asyncio
    async def test_execute_ends_meeting_when_host_ai_message_has_explicit_command(self):
        model = MagicMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])
        state = {
            "messages": [
                AIMessage(
                    content=(
                        "오늘 회의는 여기까지 정리하겠습니다.\n"
                        f"{HOST_END_MEETING_COMMAND}"
                    ),
                    name="Host",
                )
            ],
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 0,
        }

        result = await node.execute(state)

        assert result["meeting_ended"] is True
        model.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_does_not_end_meeting_when_non_host_uses_explicit_command(self):
        model = MagicMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])
        state = {
            "messages": [AIMessage(content=HOST_END_MEETING_COMMAND, name="PM")],
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "pending_speakers": ["PM"],
            "speaker_counts": {},
            "turn_count": 0,
        }

        result = await node.execute(state)

        assert result["meeting_ended"] is False
        model.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_does_not_end_meeting_when_host_ai_message_has_only_keyword(self):
        model = MagicMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])
        state = {
            "messages": [AIMessage(content="회의를 마치겠습니다.", name="Host")],
            "agendas": [{"title": "Test", "status": "completed"}],
            "current_agenda_idx": 1,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 3,
        }

        result = await node.execute(state)

        assert result["meeting_ended"] is False
        model.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_allows_human_host_keyword_fallback(self):
        model = MagicMock()
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])
        state = {
            "messages": [HumanMessage(content="회의를 마치겠습니다.", name="Host")],
            "agendas": [{"title": "Test", "status": "completed"}],
            "current_agenda_idx": 1,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 3,
        }

        result = await node.execute(state)

        assert result["meeting_ended"] is True
        model.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_decision_returns_summary(self, monkeypatch):
        """LLM이 정상 응답하면 decision 문자열을 반환."""
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="2주 단위 스프린트로 진행")
        )

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host"])

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(mention_extraction_max_tokens=64, host_checkin_interval=10),
        )

        result = await node._extract_decision("정리하면 2주 단위 스프린트로 진행합니다", "스프린트 주기")
        assert result == "2주 단위 스프린트로 진행"
        response_model.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extract_decision_returns_empty_on_failure(self, monkeypatch):
        """LLM 호출 실패 시 빈 문자열을 반환."""
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(side_effect=RuntimeError("API error"))

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host"])

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(mention_extraction_max_tokens=64, host_checkin_interval=10),
        )

        result = await node._extract_decision("다음 안건으로 넘어가겠습니다", "로드맵")
        assert result == ""

    @pytest.mark.asyncio
    async def test_execute_sets_decision_on_agenda_completion(self, monkeypatch):
        """안건 완료 시 decision 필드가 설정되는지 확인."""
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="React 기반으로 결정")
        )

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(mention_extraction_max_tokens=64, host_checkin_interval=10),
        )

        state = {
            "messages": [
                AIMessage(
                    content="정리하면 React 기반으로 진행하겠습니다. 다음 안건으로 넘어가겠습니다.",
                    name="Host",
                )
            ],
            "agendas": [
                {"title": "프레임워크 선정", "status": "in_progress"},
                {"title": "일정 논의", "status": "pending"},
            ],
            "current_agenda_idx": 0,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 0,
        }

        result = await node.execute(state)

        assert result["agendas"][0]["status"] == "completed"
        assert result["agendas"][0]["decision"] == "React 기반으로 결정"
        assert result["current_agenda_idx"] == 1
        assert result["agendas"][1]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_execute_completes_agenda_even_when_decision_extraction_fails(
        self, monkeypatch
    ):
        """decision 추출 실패해도 안건 완료 처리는 정상 동작."""
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host", "PM"])

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(mention_extraction_max_tokens=64, host_checkin_interval=10),
        )

        state = {
            "messages": [
                AIMessage(content="이 안건은 여기까지 하겠습니다.", name="Host")
            ],
            "agendas": [
                {"title": "안건1", "status": "in_progress"},
                {"title": "안건2", "status": "pending"},
            ],
            "current_agenda_idx": 0,
            "pending_speakers": ["Host"],
            "speaker_counts": {},
            "turn_count": 0,
        }

        result = await node.execute(state)

        assert result["agendas"][0]["status"] == "completed"
        assert result["current_agenda_idx"] == 1
        assert "decision" not in result["agendas"][0]


class TestHostCheckinInjection:
    """Host 주기적 체크인 주입 테스트."""

    @pytest.mark.asyncio
    async def test_host_checkin_injected_at_interval(self, monkeypatch):
        """10턴마다 Host가 pending 선두에 삽입된다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM", "TechLead"]
        )
        state = {
            "messages": [AIMessage(content="의견입니다.", name="PM")],
            "pending_speakers": ["TechLead"],
            "speaker_counts": {"PM": 5, "TechLead": 4},
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "turn_count": 9,  # +1 → 10, agenda_start=0 → agenda_turns=10
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        assert result["pending_speakers"][0] == "Host"
        assert "TechLead" in result["pending_speakers"]

    @pytest.mark.asyncio
    async def test_host_checkin_skipped_when_host_already_speaking(self, monkeypatch):
        """Host가 방금 발언한 경우 체크인 중복 삽입하지 않는다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [AIMessage(content="진행합시다.", name="Host")],
            "pending_speakers": ["PM"],
            "speaker_counts": {"Host": 3},
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "turn_count": 9,  # +1 → 10
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        # Host가 speaker이므로 체크인 삽입하지 않음
        assert result["pending_speakers"] == ["PM"]

    @pytest.mark.asyncio
    async def test_host_checkin_skipped_when_host_already_in_pending(self, monkeypatch):
        """이미 pending에 Host가 있으면 중복 삽입하지 않는다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM", "TechLead"]
        )
        state = {
            "messages": [AIMessage(content="@Host 확인 부탁", name="PM")],
            "pending_speakers": ["Host", "TechLead"],
            "speaker_counts": {"PM": 5},
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "turn_count": 9,  # +1 → 10
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        # Host가 이미 pending에 있으므로 중복 삽입 안 함
        assert result["pending_speakers"].count("Host") == 1

    @pytest.mark.asyncio
    async def test_host_checkin_not_at_non_interval_turn(self, monkeypatch):
        """체크인 주기가 아닌 턴에서는 Host를 삽입하지 않는다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [AIMessage(content="의견입니다.", name="PM")],
            "pending_speakers": [],
            "speaker_counts": {"PM": 3},
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "turn_count": 6,  # +1 → 7, not a multiple of 10
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        assert "Host" not in result["pending_speakers"]

    @pytest.mark.asyncio
    async def test_host_checkin_uses_agenda_relative_turns(self, monkeypatch):
        """체크인은 안건 시작 턴 기준 상대 턴으로 계산된다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [AIMessage(content="의견입니다.", name="PM")],
            "pending_speakers": [],
            "speaker_counts": {"PM": 3},
            "agendas": [
                {"title": "안건1", "status": "completed"},
                {"title": "안건2", "status": "in_progress"},
            ],
            "current_agenda_idx": 1,
            "turn_count": 24,  # +1 → 25, start=15, agenda_turns=10
            "current_agenda_start_turn": 15,
        }

        result = await node.execute(state)

        assert result["pending_speakers"][0] == "Host"

    @pytest.mark.asyncio
    async def test_host_checkin_disabled_when_interval_zero(self, monkeypatch):
        """host_checkin_interval=0이면 체크인이 비활성화된다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=0,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [AIMessage(content="의견입니다.", name="PM")],
            "pending_speakers": [],
            "speaker_counts": {"PM": 3},
            "agendas": [{"title": "Test", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "turn_count": 9,
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        assert "Host" not in result["pending_speakers"]


class TestAgendaStartTurnTracking:
    """current_agenda_start_turn 추적 테스트."""

    @pytest.mark.asyncio
    async def test_agenda_start_turn_updated_on_transition(self, monkeypatch):
        """안건 전환 시 current_agenda_start_turn이 갱신된다."""
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="다음 안건으로")
        )
        model = MagicMock()
        model.bind.return_value = response_model

        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )

        node = ProcessResponseNode(
            model=model, valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [
                AIMessage(content="정리하면 마무리하겠습니다. 다음 안건으로.", name="Host")
            ],
            "agendas": [
                {"title": "안건1", "status": "in_progress"},
                {"title": "안건2", "status": "pending"},
            ],
            "current_agenda_idx": 0,
            "pending_speakers": ["Host"],
            "speaker_counts": {"Host": 5},
            "turn_count": 14,  # +1 → 15
            "current_agenda_start_turn": 0,
        }

        result = await node.execute(state)

        assert result["current_agenda_idx"] == 1
        assert result["current_agenda_start_turn"] == 15

    @pytest.mark.asyncio
    async def test_agenda_start_turn_preserved_on_same_agenda(self, monkeypatch):
        """같은 안건 내에서는 current_agenda_start_turn이 유지된다."""
        monkeypatch.setattr(
            "doorae.graph.nodes.process.get_settings",
            lambda: MagicMock(
                host_checkin_interval=10,
                mention_extraction_max_tokens=64,
            ),
        )
        node = ProcessResponseNode(
            model=MagicMock(), valid_speakers=["Host", "PM"]
        )
        state = {
            "messages": [AIMessage(content="의견입니다.", name="PM")],
            "agendas": [{"title": "안건1", "status": "in_progress"}],
            "current_agenda_idx": 0,
            "pending_speakers": ["PM"],
            "speaker_counts": {"PM": 3},
            "turn_count": 7,
            "current_agenda_start_turn": 5,
        }

        result = await node.execute(state)

        assert result["current_agenda_start_turn"] == 5
