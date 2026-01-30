from functools import lru_cache
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


@lru_cache
def get_settings() -> Settings:
    """싱글톤 패턴으로 Settings 인스턴스 반환."""
    return Settings()
