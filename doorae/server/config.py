"""서버 설정 관리 모듈."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """WebSocket 채팅 서버 설정 클래스."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SERVER_",
        extra="ignore",
    )

    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000

    # 회의방 설정
    max_rooms: int = 100


@lru_cache
def get_server_settings() -> ServerSettings:
    """캐싱된 ServerSettings 인스턴스 반환."""
    return ServerSettings()
