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

    # === 공통 설정 (Fallback) ===
    openai_api_key: Optional[str] = None  # Main/Task 공통 fallback
    openai_base_url: Optional[str] = None  # 선택적 (기본: OpenAI 공식 엔드포인트)

    # === Main LLM (회의 에이전트 응답 생성) ===
    llm_main_api_key: Optional[str] = None  # Main LLM 전용 (None이면 openai_api_key 사용)
    llm_main_base_url: Optional[str] = None  # Main LLM 전용 (None이면 openai_base_url 사용)
    llm_main_model: str = "gpt-4o-mini"
    llm_main_temperature: float = 0.7
    llm_main_max_tokens: int = 4096  # 응답 최대 토큰 (기본값)

    # === Task LLM (작은 작업: 멘션 추출, 종료 감지, 안건 분석) ===
    llm_task_api_key: Optional[str] = None  # Task LLM 전용 (None이면 openai_api_key 사용)
    llm_task_base_url: Optional[str] = None  # Task LLM 전용 (None이면 openai_base_url 사용)
    llm_task_model: str = "gpt-4o-mini"  # 나중에 gpt-3.5-turbo 등으로 변경 가능
    llm_task_temperature: float = 0.0    # 일관된 결과 위해 낮게
    llm_task_max_tokens: int = 2048  # Task LLM은 더 짧은 응답

    # LLM 연결 설정
    llm_timeout: float = 60.0  # 초 단위
    llm_max_retries: int = 3

    # LangGraph 설정
    recursion_limit: int = 1000  # LangGraph 재귀 깊이 제한
    max_turns: int = 1000  # 회의 최대 턴 수 (무한루프 방지)
    
    agent_profiles_path: str = "config/agent_profiles.yaml"
    agendas_path: str = "config/agendas.yaml"

    # 대화 요약 설정
    max_messages_before_summary: int = 5  # 이 개수 초과 시 요약
    keep_recent_messages: int = 3  # 최근 몇 개 유지
    summary_max_tokens: int = 3000  # 요약 최대 토큰

    # LangSmith 설정
    langchain_tracing_v2: bool = False  # 기본값: 비활성화
    langchain_api_key: Optional[str] = None
    langchain_project: str = "thetable"  # 기본 프로젝트명
    langchain_endpoint: Optional[str] = None

    # === Property: Fallback 처리 ===
    @property
    def main_api_key(self) -> str:
        """Main LLM API 키 (fallback: openai_api_key)"""
        key = self.llm_main_api_key or self.openai_api_key
        if not key:
            raise ValueError(
                "Main LLM API key is required.\n"
                "Please set one of the following in your .env file:\n"
                "  - LLM_MAIN_API_KEY (Main LLM 전용)\n"
                "  - OPENAI_API_KEY (공통 fallback)"
            )
        return key

    @property
    def main_base_url(self) -> Optional[str]:
        """Main LLM Base URL (fallback: openai_base_url)"""
        return self.llm_main_base_url or self.openai_base_url

    @property
    def task_api_key(self) -> str:
        """Task LLM API 키 (fallback: openai_api_key)"""
        key = self.llm_task_api_key or self.openai_api_key
        if not key:
            raise ValueError(
                "Task LLM API key is required.\n"
                "Please set one of the following in your .env file:\n"
                "  - LLM_TASK_API_KEY (Task LLM 전용)\n"
                "  - OPENAI_API_KEY (공통 fallback)"
            )
        return key

    @property
    def task_base_url(self) -> Optional[str]:
        """Task LLM Base URL (fallback: openai_base_url)"""
        return self.llm_task_base_url or self.openai_base_url


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
