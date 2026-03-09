"""NodeRegistry 테스트"""

import pytest
from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.registry import NodeRegistry, register_node
from doorae.graph.state import MeetingState


@pytest.fixture(autouse=True)
def clear_registry():
    """각 테스트 전후로 레지스트리 초기화"""
    original_nodes = NodeRegistry._nodes.copy()
    NodeRegistry._nodes.clear()
    yield
    NodeRegistry._nodes = original_nodes


class TestNodeRegistry:
    """NodeRegistry 클래스 테스트"""

    def test_register_node_with_name(self):
        """명시적 이름으로 노드 등록"""

        @register_node("test_node")
        class TestNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        assert "test_node" in NodeRegistry._nodes
        assert NodeRegistry._nodes["test_node"] is TestNode

    def test_register_node_without_name(self):
        """클래스명으로 노드 등록"""

        @register_node()
        class AutoNameNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        assert "AutoNameNode" in NodeRegistry._nodes
        assert NodeRegistry._nodes["AutoNameNode"] is AutoNameNode

    def test_register_node_with_category(self):
        """카테고리와 함께 노드 등록"""

        @register_node("cat_node", category="agents")
        class CategoryNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        assert CategoryNode._registry_name == "cat_node"
        assert CategoryNode._registry_category == "agents"

    def test_get_existing_node(self):
        """등록된 노드 조회"""

        @register_node("existing")
        class ExistingNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        result = NodeRegistry.get("existing")
        assert result is ExistingNode

    def test_get_nonexistent_node_raises_error(self):
        """없는 노드 조회 시 에러 발생"""
        with pytest.raises(KeyError) as exc_info:
            NodeRegistry.get("nonexistent")

        assert "nonexistent" in str(exc_info.value)

    def test_create_node_instance(self):
        """노드 인스턴스 생성"""

        @register_node("creatable")
        class CreatableNode(BaseNode):
            def __init__(self, value):
                self.value = value

            async def execute(self, state: MeetingState):
                return {"value": self.value}

        instance = NodeRegistry.create("creatable", value=42)

        assert isinstance(instance, CreatableNode)
        assert instance.value == 42

    def test_list_all_nodes(self):
        """모든 노드 목록 조회"""

        @register_node("node1")
        class Node1(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        @register_node("node2")
        class Node2(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        nodes = NodeRegistry.list_nodes()

        assert len(nodes) == 2
        assert "node1" in nodes
        assert "node2" in nodes

    def test_list_nodes_by_category(self):
        """카테고리별 노드 목록 조회"""

        @register_node("agent1", category="agents")
        class Agent1(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        @register_node("util1", category="utility")
        class Util1(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        agents = NodeRegistry.list_nodes(category="agents")
        utils = NodeRegistry.list_nodes(category="utility")

        assert len(agents) == 1
        assert "agent1" in agents
        assert len(utils) == 1
        assert "util1" in utils

    def test_multiple_registrations_same_name(self):
        """같은 이름으로 여러 번 등록 시 마지막 것이 유지"""

        @register_node("duplicate")
        class FirstNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        @register_node("duplicate")
        class SecondNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        result = NodeRegistry.get("duplicate")
        assert result is SecondNode

    def test_discover_plugins_no_package(self):
        """없는 플러그인 패키지 - 에러 없이 처리"""
        # 에러가 발생하지 않아야 함
        NodeRegistry.discover_plugins("nonexistent_package")

    def test_registry_decorator_returns_class(self):
        """데코레이터가 클래스를 반환하는지 확인"""

        @register_node("decorated")
        class DecoratedNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        # 데코레이터가 클래스를 반환해야 함
        assert DecoratedNode.__name__ == "DecoratedNode"


class TestRegisterNodeFunction:
    """register_node 함수 테스트"""

    def test_register_node_function_works(self):
        """register_node 함수가 정상 작동하는지 확인"""

        @register_node("func_test")
        class FuncTestNode(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        assert "func_test" in NodeRegistry._nodes

    def test_register_node_creates_same_result_as_registry(self):
        """register_node와 NodeRegistry.register가 같은 결과를 생성"""

        @register_node("func1")
        class Node1(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        @NodeRegistry.register("func2")
        class Node2(BaseNode):
            async def execute(self, state: MeetingState):
                return {}

        # 둘 다 레지스트리에 등록되어야 함
        assert "func1" in NodeRegistry._nodes
        assert "func2" in NodeRegistry._nodes
