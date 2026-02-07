"""SummarizationNode 테스트"""

import pytest
from unittest.mock import MagicMock
from thetable.graph.nodes.summarize import SummarizationNode, NodeType
from thetable.graph.state import MeetingState


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
            "thetable.graph.nodes.summarize.get_settings",
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
