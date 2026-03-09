"""회의방 관리자."""

import uuid
from typing import Dict, Optional
from doorae.server.room import Room
from doorae.server.config import get_server_settings


class RoomManager:
    """회의방을 관리하는 싱글톤 클래스.

    Attributes:
        rooms: room_id를 키로, Room을 값으로 하는 딕셔너리
        max_rooms: 최대 회의방 수
    """

    def __init__(self):
        """초기화."""
        self.rooms: Dict[str, Room] = {}
        settings = get_server_settings()
        self.max_rooms = settings.max_rooms

    def create_room(self, name: str, agenda: Optional[str] = None) -> Room:
        """회의방 생성.

        Args:
            name: 회의방 이름
            agenda: 회의 안건 (선택적)

        Returns:
            생성된 Room 객체

        Raises:
            ValueError: 최대 회의방 수 초과 시
        """
        if len(self.rooms) >= self.max_rooms:
            raise ValueError(f"최대 회의방 수({self.max_rooms})를 초과했습니다.")

        room_id = str(uuid.uuid4())
        room = Room(room_id=room_id, name=name, agenda=agenda)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """회의방 조회.

        Args:
            room_id: 회의방 ID

        Returns:
            Room 객체 또는 None
        """
        return self.rooms.get(room_id)

    def delete_room(self, room_id: str) -> bool:
        """회의방 삭제.

        Args:
            room_id: 회의방 ID

        Returns:
            삭제 성공 여부
        """
        if room_id in self.rooms:
            del self.rooms[room_id]
            return True
        return False

    def list_rooms(self) -> list[dict]:
        """모든 회의방 목록 반환.

        Returns:
            회의방 정보 딕셔너리 리스트
        """
        return [room.get_info() for room in self.rooms.values()]


# 싱글톤 인스턴스
_room_manager_instance: Optional[RoomManager] = None


def get_room_manager() -> RoomManager:
    """RoomManager 싱글톤 인스턴스 반환.

    Returns:
        RoomManager 인스턴스
    """
    global _room_manager_instance
    if _room_manager_instance is None:
        _room_manager_instance = RoomManager()
    return _room_manager_instance
