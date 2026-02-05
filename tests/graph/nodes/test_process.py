"""ProcessResponseNode 테스트"""

import pytest
from thetable.graph.nodes.process import ProcessResponseNode, NodeType


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
