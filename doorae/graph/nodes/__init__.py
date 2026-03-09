"""노드 시스템 - 워크플로우 구성 요소

이 패키지는 LangGraph 워크플로우를 구성하는 노드들을 제공합니다.

주요 구성요소:
- BaseNode: 모든 노드의 추상 베이스 클래스
- NodeRegistry: 노드 플러그인 레지스트리 시스템
- ProcessResponseNode: 에이전트 응답 처리
- RefillSpeakersNode: pending_speakers 채우기
- SummarizationNode: 대화 요약 관리
- condition_router: 라우팅 함수
"""

from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.registry import NodeRegistry, register_node
from doorae.graph.nodes.agent import AgentNode
from doorae.graph.nodes.human import HumanNode
from doorae.graph.nodes.process import ProcessResponseNode
from doorae.graph.nodes.refill import RefillSpeakersNode
from doorae.graph.nodes.summarize import SummarizationNode
from doorae.graph.nodes.router import condition_router
from doorae.graph.nodes.utils import initialize_mcp_tools

__all__ = [
    # 기반 클래스
    "BaseNode",
    "NodeType",
    # 레지스트리
    "NodeRegistry",
    "register_node",
    # 노드 클래스
    "AgentNode",
    "HumanNode",
    "ProcessResponseNode",
    "RefillSpeakersNode",
    "SummarizationNode",
    # 라우터
    "condition_router",
    # 유틸리티 함수
    "initialize_mcp_tools",
]
