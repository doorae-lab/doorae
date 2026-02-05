"""BaseNode 및 NodeType 테스트"""

import pytest
from thetable.graph.nodes.base import BaseNode, NodeType
from thetable.graph.state import MeetingState


class TestNodeType:
    """NodeType enum 테스트"""

    def test_node_types_exist(self):
        """모든 노드 타입이 정의되어 있는지 확인"""
        assert NodeType.AGENT
        assert NodeType.UTILITY
        assert NodeType.HUMAN
        assert NodeType.ROUTING

    def test_node_types_unique(self):
        """노드 타입이 고유한지 확인"""
        types = [NodeType.AGENT, NodeType.UTILITY, NodeType.HUMAN, NodeType.ROUTING]
        assert len(types) == len(set(types))


class ConcreteNode(BaseNode):
    """테스트용 구체적인 노드 구현"""

    def __init__(self, return_value=None):
        self.return_value = return_value or {"test": "value"}
        self.on_enter_called = False
        self.on_exit_called = False

    async def execute(self, state: MeetingState):
        return self.return_value

    async def on_enter(self, state: MeetingState):
        self.on_enter_called = True

    async def on_exit(self, state: MeetingState, result: dict):
        self.on_exit_called = True
        return result


class TestBaseNode:
    """BaseNode 추상 클래스 테스트"""

    def test_cannot_instantiate_base_node(self):
        """BaseNode는 직접 인스턴스화할 수 없음"""
        with pytest.raises(TypeError):
            BaseNode()

    @pytest.mark.asyncio
    async def test_execute_required(self):
        """execute 메서드가 구현되어야 함"""

        class IncompleteNode(BaseNode):
            pass

        with pytest.raises(TypeError):
            IncompleteNode()

    @pytest.mark.asyncio
    async def test_call_invokes_hooks_and_execute(self):
        """__call__이 on_enter, execute, on_exit을 순서대로 호출"""
        node = ConcreteNode()
        state = MeetingState(messages=[], pending_speakers=[])

        result = await node(state)

        assert node.on_enter_called
        assert node.on_exit_called
        assert result == {"test": "value"}

    @pytest.mark.asyncio
    async def test_on_enter_hook(self):
        """on_enter 훅이 실행되는지 확인"""

        class TestNode(BaseNode):
            def __init__(self):
                self.enter_state = None

            async def on_enter(self, state: MeetingState):
                self.enter_state = state

            async def execute(self, state: MeetingState):
                return {}

        node = TestNode()
        state = MeetingState(messages=[], pending_speakers=[])

        await node(state)

        assert node.enter_state is state

    @pytest.mark.asyncio
    async def test_on_exit_hook_can_modify_result(self):
        """on_exit 훅이 결과를 수정할 수 있는지 확인"""

        class TestNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {"original": "value"}

            async def on_exit(self, state: MeetingState, result: dict):
                result["modified"] = True
                return result

        node = TestNode()
        state = MeetingState(messages=[], pending_speakers=[])

        result = await node(state)

        assert result == {"original": "value", "modified": True}

    def test_default_attributes(self):
        """기본 속성값 확인"""
        node = ConcreteNode()

        assert node.node_type == NodeType.UTILITY
        assert node.requires_llm is False
        assert node.requires_tools is False

    def test_custom_attributes(self):
        """커스텀 속성 설정 확인"""

        class CustomNode(BaseNode):
            node_type = NodeType.AGENT
            requires_llm = True
            requires_tools = True

            async def execute(self, state: MeetingState):
                return {}

        node = CustomNode()

        assert node.node_type == NodeType.AGENT
        assert node.requires_llm is True
        assert node.requires_tools is True
