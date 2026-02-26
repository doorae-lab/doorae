"""ProcessResponseNode 테스트"""

import inspect
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
        from unittest.mock import MagicMock

        node = ProcessResponseNode(model=MagicMock(), valid_speakers=["Host"])

        assert node._detect_meeting_end_keyword("회의를 마치겠습니다") is True
        assert node._detect_meeting_end_keyword("수고하셨습니다") is True
        assert node._detect_meeting_end_keyword("다음 안건으로 이동합니다") is False
