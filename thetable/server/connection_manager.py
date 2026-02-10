"""WebSocket 연결 관리자."""

from typing import Dict
from fastapi import WebSocket


class ConnectionManager:
    """WebSocket 연결을 관리하는 클래스.

    Attributes:
        connections: username을 키로, WebSocket을 값으로 하는 딕셔너리
    """

    def __init__(self):
        """초기화."""
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        """WebSocket 연결을 수락하고 저장.

        Args:
            username: 사용자 이름
            websocket: WebSocket 연결
        """
        await websocket.accept()
        self.connections[username] = websocket

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
        if username in self.connections:
            await self.connections[username].send_text(message)

    async def broadcast(self, message: str):
        """모든 연결된 사용자에게 메시지 브로드캐스트.

        Args:
            message: 전송할 메시지
        """
        for connection in self.connections.values():
            await connection.send_text(message)

    def get_connection_count(self) -> int:
        """현재 연결된 사용자 수 반환.

        Returns:
            연결된 사용자 수
        """
        return len(self.connections)

    def is_connected(self, username: str) -> bool:
        """사용자가 연결되어 있는지 확인.

        Args:
            username: 사용자 이름

        Returns:
            연결 여부
        """
        return username in self.connections
