"""유틸리티 함수들 - 회의 워크플로우 헬퍼"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def initialize_mcp_tools(config_path: Optional[str] = None) -> dict[str, list]:
    """MCP tools 초기화 및 서버별 수집

    Args:
        config_path: mcp_servers.json 경로 (None이면 config/mcp_servers.json)

    Returns:
        서버별 tools 딕셔너리 {server_name: [tools]}
    """
    from pathlib import Path

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from thetable.mcp import load_mcp_config, collect_tools_by_server

        # MCP 설정 로드
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"
            )

        config_dict = load_mcp_config(config_path)

        if not config_dict:
            logger.warning("⚠️ 사용 가능한 MCP 서버가 없습니다")
            return {}

        # MCP 클라이언트 초기화
        mcp_client = MultiServerMCPClient(config_dict)

        # 모든 서버의 tools 수집
        server_names = set(config_dict.keys())
        tools_by_server = await collect_tools_by_server(mcp_client, server_names)

        total = sum(len(t) for t in tools_by_server.values())
        logger.info(f"✅ MCP 도구 로드 완료: {total}개 도구 ({len(tools_by_server)}개 서버)")

        return tools_by_server

    except ImportError:
        logger.warning("⚠️ langchain-mcp-adapters가 설치되지 않았습니다")
        return {}
    except FileNotFoundError:
        logger.warning(f"⚠️ MCP 설정 파일을 찾을 수 없습니다: {config_path}")
        return {}
    except Exception:
        logger.exception("❌ MCP 초기화 중 예상치 못한 오류 발생")
        raise
