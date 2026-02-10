"""회의방 클래스."""

import asyncio
from datetime import datetime
from typing import Optional
from thetable.server.connection_manager import ConnectionManager


class Room:
    """회의방 클래스.

    Attributes:
        id: 회의방 ID
        name: 회의방 이름
        agenda: 회의 안건
        created_at: 생성 시간
        connection_manager: WebSocket 연결 관리자
        input_queues: username별 입력 큐 딕셔너리
        workflow: LangGraph 워크플로우 (선택적)
    """

    def __init__(
        self,
        room_id: str,
        name: str,
        agenda: Optional[str] = None,
    ):
        """초기화.

        Args:
            room_id: 회의방 ID
            name: 회의방 이름
            agenda: 회의 안건 (선택적)
        """
        self.id = room_id
        self.name = name
        self.agenda = agenda
        self.created_at = datetime.now()
        self.connection_manager = ConnectionManager()
        self.input_queues: dict[str, asyncio.Queue] = {}
        self.workflow = None

    def get_info(self) -> dict:
        """회의방 정보 반환.

        Returns:
            회의방 정보 딕셔너리
        """
        return {
            "id": self.id,
            "name": self.name,
            "agenda": self.agenda,
            "created_at": self.created_at,
            "participants_count": self.connection_manager.get_connection_count(),
        }

    def create_user_queue(self, username: str) -> asyncio.Queue:
        """사용자 입력 큐 생성.

        Args:
            username: 사용자 이름

        Returns:
            생성된 asyncio.Queue
        """
        if username not in self.input_queues:
            self.input_queues[username] = asyncio.Queue()
        return self.input_queues[username]

    def get_user_queue(self, username: str) -> Optional[asyncio.Queue]:
        """사용자 입력 큐 반환.

        Args:
            username: 사용자 이름

        Returns:
            입력 큐 또는 None
        """
        return self.input_queues.get(username)

    def remove_user_queue(self, username: str):
        """사용자 입력 큐 제거.

        Args:
            username: 사용자 이름
        """
        if username in self.input_queues:
            del self.input_queues[username]
