import os
import pytest
from pydantic import ValidationError
from thetable.config import Settings, get_settings


class TestSettings:
    """Settings 클래스 테스트."""

    def test_load_from_env(self, monkeypatch):
        """환경 변수에서 설정 로드."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")

        get_settings.cache_clear()
        settings = Settings()

        assert settings.openai_api_key == "test-key-123"
        assert settings.llm_model == "gpt-4"
        assert settings.llm_temperature == 0.5

    def test_default_values(self, monkeypatch):
        """기본값 적용 테스트."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-456")

        get_settings.cache_clear()
        settings = Settings()

        assert settings.llm_model == "gpt-4o-mini"
        assert settings.llm_temperature == 0.7
        assert settings.agent_profiles_path == "config/agent_profiles.yaml"

    def test_missing_api_key(self, monkeypatch):
        """API 키 누락 시 ValidationError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        get_settings.cache_clear()
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "openai_api_key" in str(exc_info.value).lower()

    def test_singleton_pattern(self, monkeypatch):
        """싱글톤 패턴 동작 테스트."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-789")

        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_openai_base_url_optional(self, monkeypatch):
        """OpenAI base_url은 선택적 필드."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-base")

        get_settings.cache_clear()
        settings = Settings()

        assert settings.openai_base_url is None

    def test_openai_base_url_custom(self, monkeypatch):
        """커스텀 OpenAI base_url 설정."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-custom")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.openai.com/v1")

        get_settings.cache_clear()
        settings = Settings()

        assert settings.openai_base_url == "https://custom.openai.com/v1"
