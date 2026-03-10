"""SummarizationNode 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from doorae.graph.nodes.summarize import SummarizationNode, NodeType
from doorae.graph.state import MeetingState


class TestSummarizationNode:
    """SummarizationNode 클래스 테스트"""

    def test_node_type(self):
        """노드 타입이 UTILITY인지 확인"""
        assert SummarizationNode.node_type == NodeType.UTILITY

    def test_requires_llm(self):
        """LLM이 필요한 노드인지 확인"""
        assert SummarizationNode.requires_llm is True

    def test_initialization(self):
        """초기화 테스트"""
        mock_model = MagicMock()
        node = SummarizationNode(model=mock_model)

        assert node.model is mock_model

    @pytest.mark.asyncio
    async def test_no_summarization_when_few_messages(self, monkeypatch):
        """메시지가 적으면 요약하지 않음"""
        monkeypatch.setattr(
            "doorae.graph.nodes.summarize.get_settings",
            lambda: MagicMock(max_messages_before_summary=10),
        )

        mock_model = MagicMock()
        node = SummarizationNode(model=mock_model)

        # 메시지 5개만 추가
        messages = []
        for i in range(5):
            msg = MagicMock()
            msg.id = f"msg_{i}"
            msg.content = f"메시지 {i}"
            msg.name = "Alice"
            messages.append(msg)

        state = MeetingState(messages=messages, summary="")

        result = await node.execute(state)

        assert result == {}  # 변경 없음

    @pytest.mark.asyncio
    async def test_no_summarization_when_too_few_non_empty_messages(self, monkeypatch):
        """요약 대상 실질 메시지가 적으면 요약하지 않음"""
        monkeypatch.setattr(
            "doorae.graph.nodes.summarize.get_settings",
            lambda: MagicMock(
                max_messages_before_summary=3,
                keep_recent_messages=3,
                summary_max_tokens=3000,
            ),
        )

        mock_model = MagicMock()
        node = SummarizationNode(model=mock_model)

        messages = []
        raw_messages = [
            ("msg_0", "Alice", "첫 번째"),
            ("msg_1", "Alice", ""),
            ("msg_2", "Alice", "   "),
            ("msg_3", "Bob", "최근 1"),
            ("msg_4", "Bob", "최근 2"),
            ("msg_5", "Bob", "최근 3"),
        ]
        for msg_id, name, content in raw_messages:
            msg = MagicMock()
            msg.id = msg_id
            msg.content = content
            msg.name = name
            messages.append(msg)

        state = MeetingState(messages=messages, summary="")

        result = await node.execute(state)

        assert result == {}
        mock_model.bind.assert_not_called()

    @pytest.mark.asyncio
    async def test_summarization_binds_summary_max_tokens(self, monkeypatch):
        """요약 시 summary_max_tokens로 바인딩"""
        monkeypatch.setattr(
            "doorae.graph.nodes.summarize.get_settings",
            lambda: MagicMock(
                max_messages_before_summary=3,
                keep_recent_messages=1,
                summary_max_tokens=1234,
            ),
        )

        response_model = MagicMock()
        response_model.ainvoke = AsyncMock(return_value=MagicMock(content="요약"))
        mock_model = MagicMock()
        mock_model.bind.return_value = response_model
        node = SummarizationNode(model=mock_model)

        messages = []
        for i in range(5):
            msg = MagicMock()
            msg.id = f"msg_{i}"
            msg.content = f"메시지 {i}"
            msg.name = "Alice"
            messages.append(msg)

        state = MeetingState(messages=messages, summary="")

        result = await node.execute(state)

        assert result["summary"] == "요약"
        mock_model.bind.assert_called_once_with(max_tokens=1234)
        response_model.ainvoke.assert_awaited_once()
