"""
doorae.server - WebSocket 채팅 서버

LangGraph 워크플로우 기반 실시간 회의 채팅 서버
"""

import uvicorn
from doorae.server.config import get_server_settings


def main():
    """서버 엔트리포인트."""
    settings = get_server_settings()
    uvicorn.run(
        "doorae.server.app:create_app",
        host=settings.host,
        port=settings.port,
        factory=True,
        reload=False,
    )
