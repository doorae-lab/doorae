"""FastAPI 라우트 정의."""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from doorae.config import get_settings
from doorae.core.profile import AgentProfile
from doorae.graph.input_provider import QueueInputProvider
from doorae.interfaces.engine import MeetingEngine
from doorae.server.models import RoomCreate, RoomInfo
from doorae.server.room_manager import get_room_manager
from doorae.server.events import format_system_event

logger = logging.getLogger(__name__)


router = APIRouter()


def _build_runtime_human_profiles(usernames: list[str]) -> dict[str, AgentProfile]:
    """웹소켓 참가자 목록으로 런타임 human 프로필을 생성한다."""
    return {
        username: AgentProfile(
            name=username,
            role="participant",
            responsibilities=["회의 참여", "의견 제시"],
            expertise=["일반"],
            is_human=True,
        )
        for username in usernames
    }


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
    username: str = Query(..., description="사용자 이름"),
    raw_events: bool = Query(True, description="raw 이벤트 구독 여부"),
):
    """WebSocket 채팅 엔드포인트.

    워크플로우가 설정된 Room에서는 사용자 입력을 Queue로 전달하고,
    astream_events를 통한 AI 응답을 WebSocket으로 중계합니다.

    Args:
        websocket: WebSocket 연결
        room_id: 회의방 ID
        username: 사용자 이름 (쿼리 파라미터)
        raw_events: raw 이벤트 구독 여부
    """
    room_manager = get_room_manager()
    room = room_manager.get_room(room_id)

    if room is None:
        await websocket.close(code=4004, reason="회의방을 찾을 수 없습니다.")
        return

    await room.join(username, websocket, raw_events=raw_events)
    try:
        while True:
            data = await websocket.receive_text()
            await room.handle_message(username, data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for {username} in room {room_id}: {e}")
    finally:
        await room.leave(username)


@router.post("/api/rooms/{room_id}/start")
async def start_room_workflow(room_id: str):
    """Room의 AI 워크플로우를 시작.

    Args:
        room_id: 회의방 ID

    Returns:
        시작 결과 메시지
    """
    room_manager = get_room_manager()
    room = room_manager.get_room(room_id)

    if room is None:
        raise HTTPException(status_code=404, detail="회의방을 찾을 수 없습니다.")

    if room.workflow is not None:
        raise HTTPException(status_code=409, detail="워크플로우가 이미 실행 중입니다.")

    participants = list(room.connection_manager.connections.keys())
    if not participants:
        raise HTTPException(
            status_code=400,
            detail="참가자가 없습니다. 먼저 WebSocket으로 연결해 주세요.",
        )

    settings = get_settings()

    # 참가자별 입력 큐 준비
    for username in participants:
        room.create_user_queue(username)

    input_provider = QueueInputProvider(queue_getter=room.get_user_queue)
    runtime_profiles = _build_runtime_human_profiles(participants)
    engine = MeetingEngine(
        initial_message="회의를 시작합니다",
        settings=settings,
        profiles_path=settings.agent_profiles_path,
        input_provider=input_provider,
        profiles_override=runtime_profiles,
    )
    await room.start_workflow_streaming(engine=engine)

    # 시작 알림 브로드캐스트
    start_event = format_system_event("AI 워크플로우가 시작되었습니다.")
    await room.connection_manager.broadcast(json.dumps(start_event))

    return {"status": "started", "room_id": room_id}
