"""ProcessResponseNode 테스트"""

import inspect
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from unittest.mock import AsyncMock, MagicMock
from doorae.graph.nodes.process import ProcessResponseNode, NodeType


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
            lambda: MagicMock(mention_extraction_max_tokens=64),
        )

        mentions = await node._extract_mentions(
            HumanMessage(content="누가 답변하면 좋을까요? 의견 부탁드립니다.", name="chulsoo")
        )

        assert mentions == ["PM"]
        model.bind.assert_called_once_with(max_tokens=64)
        response_model.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_detect_meeting_end_llm_uses_small_token_cap(self):
        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(return_value=MagicMock(content="예"))

        model = MagicMock()
        model.bind.return_value = response_model
        node = ProcessResponseNode(model=model, valid_speakers=["Host"])

        result = await node._detect_meeting_end_llm("회의를 마칠까요?")

        assert result is True
        model.bind.assert_called_once_with(max_tokens=16)
        response_model.ainvoke.assert_awaited_once()

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
