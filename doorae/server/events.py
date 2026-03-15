"""LangGraph 이벤트 변환 유틸리티."""

from datetime import datetime
from typing import Any, Dict

from doorae.interfaces.engine import MeetingEngineRuntimeState


def _to_jsonable(value: Any) -> Any:
    """JSON 직렬화 가능한 형태로 재귀 변환."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]

    if hasattr(value, "content"):
        message = {
            "content": getattr(value, "content", None),
            "type": value.__class__.__name__,
        }
        if hasattr(value, "name"):
            message["name"] = getattr(value, "name")
        if hasattr(value, "id"):
            message["id"] = getattr(value, "id")
        return _to_jsonable(message)

    if hasattr(value, "model_dump"):
        try:
            return _to_jsonable(value.model_dump())
        except Exception:
            return str(value)

    return str(value)


def event_to_dict(event: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph 이벤트를 JSON 직렬화 가능한 딕셔너리로 변환.

    Args:
        event: LangGraph 이벤트

    Returns:
        JSON 직렬화 가능한 딕셔너리
    """
    # 기본 이벤트 구조
    result = {
        "type": event.get("event", "unknown"),
        "timestamp": datetime.now().isoformat(),
    }

    # delegated_by: 태그 확인 → is_delegated 필드 포함
    tags = event.get("tags", [])
    if any(tag.startswith("delegated_by:") for tag in tags):
        result["is_delegated"] = True

    # 메타데이터 추가
    if "metadata" in event:
        result["metadata"] = _to_jsonable(event["metadata"])

    # 데이터 추가 (메시지 등)
    if "data" in event:
        result["data"] = _to_jsonable(event["data"])

    return result


def format_message_event(content: str, sender: str) -> Dict[str, Any]:
    """메시지 이벤트 포맷팅.

    Args:
        content: 메시지 내용
        sender: 발신자

    Returns:
        포맷팅된 이벤트 딕셔너리
    """
    return {
        "type": "message",
        "data": {
            "content": content,
            "sender": sender,
        },
        "timestamp": datetime.now().isoformat(),
    }


def format_error_event(error: str) -> Dict[str, Any]:
    """에러 이벤트 포맷팅.

    Args:
        error: 에러 메시지

    Returns:
        포맷팅된 이벤트 딕셔너리
    """
    return {
        "type": "error",
        "data": {
            "error": error,
        },
        "timestamp": datetime.now().isoformat(),
    }


def format_system_event(message: str) -> Dict[str, Any]:
    """시스템 이벤트 포맷팅.

    Args:
        message: 시스템 메시지

    Returns:
        포맷팅된 이벤트 딕셔너리
    """
    return {
        "type": "system",
        "data": {
            "message": message,
        },
        "timestamp": datetime.now().isoformat(),
    }


def format_semantic_event(event_type: str, **kwargs: Any) -> Dict[str, Any]:
    """MeetingEngine semantic 이벤트를 WebSocket 전송용으로 포맷팅."""
    return {
        "type": f"semantic:{event_type}",
        "data": {key: _to_jsonable(value) for key, value in kwargs.items()},
        "timestamp": datetime.now().isoformat(),
    }


def format_state_snapshot_event(
    runtime_state: MeetingEngineRuntimeState,
    top_profiles: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """회의 중간 합류 클라이언트를 위한 현재 상태 snapshot 이벤트를 포맷팅."""
    payload: dict[str, Any] = {
        "current_speaker": runtime_state.current_speaker,
        "current_delegated_speaker": runtime_state.current_delegated_speaker,
        "agendas": runtime_state.agendas,
        "current_agenda_idx": runtime_state.current_agenda_idx,
        "pending_speakers": runtime_state.pending_speakers,
        "speaker_counts": runtime_state.speaker_counts,
        "participant_statuses": runtime_state.participant_statuses,
    }
    if top_profiles:
        payload["top_profiles"] = top_profiles
    return format_semantic_event("state_snapshot", **payload)
