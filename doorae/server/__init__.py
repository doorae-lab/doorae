"""
doorae.server - WebSocket 채팅 서버

LangGraph 워크플로우 기반 실시간 회의 채팅 서버
"""

from __future__ import annotations

import sys
import warnings

from doorae.server.config import _parse_bind_address, get_server_settings

DEPRECATED_ENTRYPOINT_MESSAGE = (
    "doorae-server는 deprecated입니다. 대신 'doorae serve'를 사용하세요."
)


def run_server(server: str = "0.0.0.0:8000") -> None:
    """공통 서버 실행 로직."""
    import uvicorn

    host, port = _parse_bind_address(server)
    uvicorn.run(
        "doorae.server.app:create_app",
        host=host,
        port=port,
        factory=True,
        reload=False,
    )


def main() -> None:
    """서버 엔트리포인트."""
    warnings.warn(DEPRECATED_ENTRYPOINT_MESSAGE, DeprecationWarning, stacklevel=2)
    print(DEPRECATED_ENTRYPOINT_MESSAGE, file=sys.stderr)

    settings = get_server_settings()
    run_server(settings.server_address)
