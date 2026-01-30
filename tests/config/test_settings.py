import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError
from thetable.config import Settings, get_settings
from thetable.config.settings import _get_cached_settings


class TestSettings:
    """Settings 클래스 테스트."""

    def test_load_from_env(self, monkeypatch):
        """환경 변수에서 설정 로드."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")

        _get_cached_settings.cache_clear()
        settings = Settings()

        assert settings.openai_api_key == "test-key-123"
        assert settings.llm_model == "gpt-4"
        assert settings.llm_temperature == 0.5

    def test_default_values(self, monkeypatch):
        """기본값 적용 테스트."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-456")

        _get_cached_settings.cache_clear()
        settings = Settings()

        assert settings.llm_model == "gpt-4o-mini"
        assert settings.llm_temperature == 0.7
        assert settings.agent_profiles_path == "config/agent_profiles.yaml"

    def test_missing_api_key(self, monkeypatch):
        """API 키 누락 시 ValidationError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        _get_cached_settings.cache_clear()
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        assert "openai_api_key" in str(exc_info.value).lower()

    def test_singleton_pattern(self, monkeypatch):
        """싱글톤 패턴 동작 테스트."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-789")

        _get_cached_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_openai_base_url_optional(self, monkeypatch):
        """OpenAI base_url은 선택적 필드."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-base")

        _get_cached_settings.cache_clear()
        settings = Settings()

        assert settings.openai_base_url is None

    def test_openai_base_url_custom(self, monkeypatch):
        """커스텀 OpenAI base_url 설정."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-custom")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.openai.com/v1")

        _get_cached_settings.cache_clear()
        settings = Settings()

        assert settings.openai_base_url == "https://custom.openai.com/v1"

    def test_get_settings_default(self, monkeypatch):
        """기본 설정 로드 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-default-key")

        _get_cached_settings.cache_clear()
        settings = get_settings()

        assert settings.llm_model == "gpt-4o-mini"
        assert settings.llm_temperature == 0.7

    def test_get_settings_custom_path(self, monkeypatch):
        """커스텀 경로 설정 파일 로드 테스트"""
        # 환경변수 제거 (conftest의 autouse fixture가 설정한 값 무효화)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.delenv("LLM_TEMPERATURE", raising=False)

        # 임시 .env 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("OPENAI_API_KEY=test-custom-key\n")
            f.write("LLM_MODEL=gpt-4o\n")
            f.write("LLM_TEMPERATURE=0.9\n")
            temp_path = f.name

        try:
            # 커스텀 경로로 설정 로드
            settings = get_settings(config_path=Path(temp_path))

            assert settings.openai_api_key == "test-custom-key"
            assert settings.llm_model == "gpt-4o"
            assert settings.llm_temperature == 0.9
        finally:
            # 임시 파일 삭제
            os.unlink(temp_path)
