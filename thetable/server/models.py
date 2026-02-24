"""서버 데이터 모델 정의."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    """회의방 생성 요청 모델."""

    name: str = Field(..., min_length=1, max_length=100)
    agenda: Optional[str] = Field(None, max_length=500)


class RoomInfo(BaseModel):
    """회의방 정보 응답 모델."""

    id: str
    name: str
    agenda: Optional[str] = None
    created_at: datetime
    participants_count: int = 0
