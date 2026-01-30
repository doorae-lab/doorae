from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """중앙 집중식 설정 관리 클래스."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str  # 필수
    openai_base_url: Optional[str] = None  # 선택적 (기본: OpenAI 공식 엔드포인트)
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    agent_profiles_path: str = "config/agent_profiles.yaml"


def get_settings(config_path: Optional[Path] = None) -> Settings:
    """Settings 인스턴스 반환.

    Args:
        config_path: 커스텀 .env 파일 경로 (None이면 기본 .env 사용)

    Returns:
        Settings 인스턴스

    Note:
        config_path를 지정하면 lru_cache를 우회하고 매번 새 인스턴스 생성
    """
    if config_path is not None:
        # 커스텀 경로 사용 시 캐시 우회
        return Settings(_env_file=str(config_path))

    # 기본 경로 사용 시 캐싱된 인스턴스 반환
    return _get_cached_settings()


@lru_cache
def _get_cached_settings() -> Settings:
    """캐싱된 Settings 인스턴스 반환 (내부 사용)."""
    return Settings()
