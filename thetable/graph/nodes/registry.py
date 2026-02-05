"""노드 레지스트리 - 플러그인 시스템"""

from typing import Type, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NodeRegistry:
    """노드 플러그인 레지스트리

    노드를 등록하고 조회하는 레지스트리 패턴을 구현합니다.
    플러그인 시스템을 통해 외부에서 새로운 노드를 추가할 수 있습니다.

    Example:
        >>> @register_node("my_node", category="custom")
        ... class MyNode(BaseNode):
        ...     async def execute(self, state):
        ...         return {}
        ...
        >>> node = NodeRegistry.create("my_node", **kwargs)
    """

    _nodes: Dict[str, Type["BaseNode"]] = {}

    @classmethod
    def register(cls, name: Optional[str] = None, *, category: str = "default"):
        """노드 등록 데코레이터

        Args:
            name: 노드 이름 (None이면 클래스명 사용)
            category: 노드 카테고리 (기본값: "default")

        Returns:
            노드 클래스를 등록하는 데코레이터 함수
        """

        def decorator(node_cls):
            key = name or node_cls.__name__
            cls._nodes[key] = node_cls
            node_cls._registry_name = key
            node_cls._registry_category = category
            logger.debug(f"노드 등록: {key} (카테고리: {category})")
            return node_cls

        return decorator

    @classmethod
    def get(cls, name: str) -> Type["BaseNode"]:
        """등록된 노드 클래스 조회

        Args:
            name: 노드 이름

        Returns:
            노드 클래스

        Raises:
            KeyError: 노드가 등록되지 않은 경우
        """
        if name not in cls._nodes:
            raise KeyError(
                f"노드 '{name}'을(를) 찾을 수 없습니다. "
                f"사용 가능한 노드: {list(cls._nodes.keys())}"
            )
        return cls._nodes[name]

    @classmethod
    def create(cls, name: str, **kwargs) -> "BaseNode":
        """노드 인스턴스 생성

        Args:
            name: 노드 이름
            **kwargs: 노드 생성자에 전달할 인자

        Returns:
            생성된 노드 인스턴스
        """
        node_cls = cls.get(name)
        return node_cls(**kwargs)

    @classmethod
    def list_nodes(cls, category: Optional[str] = None) -> Dict[str, Type["BaseNode"]]:
        """등록된 노드 목록 조회

        Args:
            category: 특정 카테고리의 노드만 조회 (None이면 전체)

        Returns:
            노드 이름과 클래스의 딕셔너리
        """
        if category is None:
            return cls._nodes.copy()

        return {
            name: node_cls
            for name, node_cls in cls._nodes.items()
            if getattr(node_cls, "_registry_category", "default") == category
        }

    @classmethod
    def discover_plugins(cls, package: str = "thetable_plugins"):
        """플러그인 자동 발견

        지정된 패키지에서 노드 플러그인을 자동으로 로드합니다.

        Args:
            package: 플러그인 패키지 이름
        """
        import importlib
        import pkgutil

        try:
            pkg = importlib.import_module(package)
            for _, mod_name, _ in pkgutil.iter_modules(pkg.__path__):
                try:
                    importlib.import_module(f"{package}.{mod_name}")
                    logger.info(f"플러그인 로드 성공: {package}.{mod_name}")
                except Exception as e:
                    logger.warning(f"플러그인 로드 실패: {package}.{mod_name} - {e}")
        except ImportError:
            logger.debug(f"플러그인 패키지를 찾을 수 없습니다: {package}")


def register_node(name: Optional[str] = None, *, category: str = "default"):
    """노드 등록 데코레이터 (편의 함수)

    NodeRegistry.register의 별칭입니다.

    Args:
        name: 노드 이름 (None이면 클래스명 사용)
        category: 노드 카테고리 (기본값: "default")

    Returns:
        노드 클래스를 등록하는 데코레이터 함수
    """
    return NodeRegistry.register(name, category=category)
