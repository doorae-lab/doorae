"""서버 설정 관리 모듈."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from doorae.core.server_address import (
    ServerAddressParseError,
    format_host_port,
    parse_server_address,
)


def _parse_bind_address(server_address: str) -> tuple[str, int]:
    try:
        parsed = parse_server_address(server_address)
    except ServerAddressParseError as exc:
        message_by_reason = {
            "empty": "DOORAE_SERVER는 비워둘 수 없습니다.",
            "missing_host": "DOORAE_SERVER에 호스트가 없습니다.",
            "invalid_format": "DOORAE_SERVER는 host:port 형식만 지원합니다.",
            "invalid_port": "DOORAE_SERVER의 포트 번호가 올바르지 않습니다.",
            "missing_port": "DOORAE_SERVER에 포트가 없습니다.",
        }
        raise ValueError(message_by_reason[exc.reason]) from exc
    return parsed.host, parsed.port


class ServerSettings(BaseSettings):
    """WebSocket 채팅 서버 설정 클래스."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SERVER_",
        extra="ignore",
    )

    # 서버 설정
    server: str | None = Field(default=None, validation_alias="DOORAE_SERVER")
    host: str = "0.0.0.0"
    port: int = 8000

    # 회의방 설정
    max_rooms: int = 100

    @model_validator(mode="after")
    def apply_server_override(self) -> "ServerSettings":
        if not self.server:
            return self

        host, port = _parse_bind_address(self.server)
        object.__setattr__(self, "host", host)
        object.__setattr__(self, "port", port)
        return self

    @property
    def server_address(self) -> str:
        return format_host_port(self.host, self.port)


@lru_cache
def get_server_settings() -> ServerSettings:
    """캐싱된 ServerSettings 인스턴스 반환."""
    return ServerSettings()
