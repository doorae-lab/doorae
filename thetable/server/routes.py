"""FastAPI 라우트 정의."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from thetable.server.models import RoomCreate, RoomInfo
from thetable.server.room_manager import get_room_manager
from thetable.server.events import format_message_event, format_error_event, format_system_event


router = APIRouter()


# ============================================================================
# REST API - Room 관리
# ============================================================================

@router.post("/api/rooms", response_model=RoomInfo, status_code=201)
async def create_room(room_data: RoomCreate):
    """회의방 생성.

    Args:
        room_data: 회의방 생성 데이터

    Returns:
        생성된 회의방 정보
    """
    room_manager = get_room_manager()
    try:
        room = room_manager.create_room(
            name=room_data.name,
            agenda=room_data.agenda
        )
        return RoomInfo(**room.get_info())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/rooms", response_model=list[RoomInfo])
async def list_rooms():
    """모든 회의방 목록 조회.

    Returns:
        회의방 정보 리스트
    """
    room_manager = get_room_manager()
    rooms = room_manager.list_rooms()
    return [RoomInfo(**room) for room in rooms]


@router.get("/api/rooms/{room_id}", response_model=RoomInfo)
async def get_room(room_id: str):
    """특정 회의방 정보 조회.

    Args:
        room_id: 회의방 ID

    Returns:
        회의방 정보
    """
    room_manager = get_room_manager()
    room = room_manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="회의방을 찾을 수 없습니다.")
    return RoomInfo(**room.get_info())


@router.delete("/api/rooms/{room_id}", status_code=204)
async def delete_room(room_id: str):
    """회의방 삭제.

    Args:
        room_id: 회의방 ID
    """
    room_manager = get_room_manager()
    success = room_manager.delete_room(room_id)
    if not success:
        raise HTTPException(status_code=404, detail="회의방을 찾을 수 없습니다.")


# ============================================================================
# WebSocket - 채팅
# ============================================================================

@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    username: str = Query(..., description="사용자 이름")
):
    """WebSocket 채팅 엔드포인트.

    Args:
        websocket: WebSocket 연결
        room_id: 회의방 ID
        username: 사용자 이름 (쿼리 파라미터)
    """
    room_manager = get_room_manager()
    room = room_manager.get_room(room_id)

    if room is None:
        await websocket.close(code=4004, reason="회의방을 찾을 수 없습니다.")
        return

    # 연결 수락 및 관리자에 추가
    await room.connection_manager.connect(username, websocket)

    # 입장 메시지 브로드캐스트
    join_event = format_system_event(f"{username}님이 입장했습니다.")
    await room.connection_manager.broadcast(json.dumps(join_event))

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # 메시지 이벤트 생성
            message_event = format_message_event(
                content=message_data.get("content", ""),
                sender=username
            )

            # 모든 참가자에게 브로드캐스트
            await room.connection_manager.broadcast(json.dumps(message_event))

    except WebSocketDisconnect:
        # 연결 해제 처리
        room.connection_manager.disconnect(username)

        # 퇴장 메시지 브로드캐스트
        leave_event = format_system_event(f"{username}님이 퇴장했습니다.")
        await room.connection_manager.broadcast(json.dumps(leave_event))

    except Exception as e:
        # 에러 처리
        error_event = format_error_event(str(e))
        await websocket.send_text(json.dumps(error_event))
        room.connection_manager.disconnect(username)
