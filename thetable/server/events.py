"""LangGraph 이벤트 변환 유틸리티."""

from typing import Any, Dict
from datetime import datetime


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

    # 메타데이터 추가
    if "metadata" in event:
        result["metadata"] = event["metadata"]

    # 데이터 추가 (메시지 등)
    if "data" in event:
        data = event["data"]
        # LangChain 메시지 객체 처리
        if hasattr(data, "content"):
            result["data"] = {
                "content": data.content,
                "type": data.__class__.__name__,
            }
            # name 속성이 있으면 추가
            if hasattr(data, "name"):
                result["data"]["name"] = data.name
        else:
            result["data"] = data

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
