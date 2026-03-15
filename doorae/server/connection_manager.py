"""WebSocket 연결 관리자."""

from dataclasses import dataclass
import logging
from typing import Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConnectionInfo:
    websocket: WebSocket
    raw_events: bool = True


class ConnectionManager:
    """WebSocket 연결을 관리하는 클래스.

    Attributes:
        connections: username을 키로, 연결 정보를 값으로 하는 딕셔너리
    """

    def __init__(self):
        """초기화."""
        self.connections: Dict[str, ConnectionInfo] = {}

    async def connect(
        self,
        username: str,
        websocket: WebSocket,
        raw_events: bool = True,
    ):
        """WebSocket 연결을 수락하고 저장.

        Args:
            username: 사용자 이름
            websocket: WebSocket 연결
        """
        existing = self.connections.get(username)
        if existing is not None and existing is not websocket:
            try:
                await existing.close()
            except Exception:
                logger.warning("Failed to close stale websocket for %s", username)
        await websocket.accept()
        self.connections[username] = ConnectionInfo(
            websocket=websocket,
            raw_events=raw_events,
        )

    def disconnect(self, username: str):
        """WebSocket 연결을 제거.

        Args:
            username: 사용자 이름
        """
        if username in self.connections:
            del self.connections[username]

    async def send_personal_message(self, message: str, username: str):
        """특정 사용자에게 메시지 전송.

        Args:
            message: 전송할 메시지
            username: 대상 사용자 이름
        """
        connection = self.connections.get(username)
        if connection is None:
            return

        try:
            await connection.websocket.send_text(message)
        except Exception:
            logger.warning(f"Failed to send message to {username}")
            if self.connections.get(username) is connection:
                self.disconnect(username)

    async def broadcast(self, message: str, channel: str = "all"):
        """모든 연결된 사용자에게 메시지 브로드캐스트.

        개별 연결 실패 시 해당 연결만 정리하고 나머지에는 계속 전송.
        순회 중 다른 코루틴이 connect/disconnect를 수행할 수 있으므로
        연결 목록 스냅샷을 기준으로 전송한다.

        Args:
            message: 전송할 메시지
            channel: "all", "semantic", "raw" 중 하나
        """
        disconnected: list[tuple[str, ConnectionInfo]] = []
        for username, connection in list(self.connections.items()):
            if self.connections.get(username) is not connection:
                continue
            if channel == "raw" and not connection.raw_events:
                continue
            try:
                await connection.websocket.send_text(message)
            except Exception:
                logger.warning(f"Failed to broadcast to {username}")
                if self.connections.get(username) is connection:
                    disconnected.append((username, connection))
        for username, connection in disconnected:
            if self.connections.get(username) is connection:
                self.disconnect(username)

    def get_connection_count(self) -> int:
        """현재 연결된 사용자 수 반환.

        Returns:
            연결된 사용자 수
        """
        return len(self.connections)
