import os
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError
from doorae.config import Settings, get_settings
from doorae.config.settings import _get_cached_settings


class TestSettings:
    """Settings 클래스 테스트."""

    def test_load_from_env(self, monkeypatch):
        """환경 변수에서 설정 로드."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("LLM_MAIN_MODEL", "gpt-4")
        monkeypatch.setenv("LLM_MAIN_TEMPERATURE", "0.5")
        monkeypatch.setenv("LLM_TASK_MODEL", "gpt-3.5-turbo")
        monkeypatch.setenv("LLM_TASK_TEMPERATURE", "0.0")

        _get_cached_settings.cache_clear()
        settings = Settings()

        assert settings.openai_api_key == "test-key-123"
        assert settings.llm_main_model == "gpt-4"
        assert settings.llm_main_temperature == 0.5
        assert settings.llm_task_model == "gpt-3.5-turbo"
        assert settings.llm_task_temperature == 0.0

    def test_default_values(self, monkeypatch):
        """기본값 적용 테스트."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-456")
        # 다른 환경변수 제거하여 기본값 테스트
        monkeypatch.delenv("LLM_MAIN_MODEL", raising=False)
        monkeypatch.delenv("LLM_MAIN_TEMPERATURE", raising=False)
        monkeypatch.delenv("LLM_TASK_MODEL", raising=False)
        monkeypatch.delenv("LLM_TASK_TEMPERATURE", raising=False)
        monkeypatch.delenv("AGENT_PROFILES_PATH", raising=False)

        _get_cached_settings.cache_clear()
        # .env 파일을 무시하고 환경변수만 사용
        settings = Settings(_env_file=None)

        assert settings.llm_main_model == "gpt-4o-mini"
        assert settings.llm_main_temperature == 0.7
        assert settings.llm_task_model == "gpt-4o-mini"
        assert settings.llm_task_temperature == 0.0
        assert settings.agent_profiles_path == "config/agent_profiles.yaml"

    def test_missing_api_key(self, monkeypatch):
        """API 키 누락 시 property 접근 시 ValueError."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MAIN_API_KEY", raising=False)
        monkeypatch.delenv("LLM_TASK_API_KEY", raising=False)

        _get_cached_settings.cache_clear()
        # Settings 생성은 성공 (모두 Optional)
        settings = Settings(_env_file=None)

        # Property 접근 시 ValueError 발생
        with pytest.raises(ValueError, match="Main LLM API key is required"):
            _ = settings.main_api_key

        with pytest.raises(ValueError, match="Task LLM API key is required"):
            _ = settings.task_api_key

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
        monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

        _get_cached_settings.cache_clear()
        # .env 파일을 무시하고 환경변수만 사용
        settings = Settings(_env_file=None)

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
        # get_settings()는 내부적으로 Settings()를 호출하므로,
        # 테스트를 실제 동작 방식에 맞게 수정
        monkeypatch.setenv("OPENAI_API_KEY", "test-default-key")

        _get_cached_settings.cache_clear()
        settings = get_settings()

        # .env 파일이 있으므로 그 값들이 사용됨
        assert settings.openai_api_key == "test-default-key"
        assert isinstance(settings.llm_main_model, str)
        assert isinstance(settings.llm_main_temperature, float)
        assert isinstance(settings.llm_task_model, str)
        assert isinstance(settings.llm_task_temperature, float)

    def test_get_settings_custom_path(self, monkeypatch):
        """커스텀 경로 설정 파일 로드 테스트"""
        # 환경변수 제거 (conftest의 autouse fixture가 설정한 값 무효화)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MAIN_MODEL", raising=False)
        monkeypatch.delenv("LLM_MAIN_TEMPERATURE", raising=False)
        monkeypatch.delenv("LLM_TASK_MODEL", raising=False)
        monkeypatch.delenv("LLM_TASK_TEMPERATURE", raising=False)

        # 임시 .env 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("OPENAI_API_KEY=test-custom-key\n")
            f.write("LLM_MAIN_MODEL=gpt-4o\n")
            f.write("LLM_MAIN_TEMPERATURE=0.9\n")
            f.write("LLM_TASK_MODEL=gpt-3.5-turbo\n")
            f.write("LLM_TASK_TEMPERATURE=0.0\n")
            temp_path = f.name

        try:
            # 커스텀 경로로 설정 로드
            settings = get_settings(config_path=Path(temp_path))

            assert settings.openai_api_key == "test-custom-key"
            assert settings.llm_main_model == "gpt-4o"
            assert settings.llm_main_temperature == 0.9
            assert settings.llm_task_model == "gpt-3.5-turbo"
            assert settings.llm_task_temperature == 0.0
        finally:
            # 임시 파일 삭제
            os.unlink(temp_path)

    def test_main_api_key_fallback(self, monkeypatch):
        """Main API 키 fallback 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-common")
        monkeypatch.delenv("LLM_MAIN_API_KEY", raising=False)

        _get_cached_settings.cache_clear()
        settings = Settings(_env_file=None)

        # llm_main_api_key 없으면 openai_api_key 사용
        assert settings.main_api_key == "sk-common"

    def test_main_api_key_override(self, monkeypatch):
        """Main API 키 전용 설정 우선순위 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-common")
        monkeypatch.setenv("LLM_MAIN_API_KEY", "sk-main-only")

        _get_cached_settings.cache_clear()
        settings = Settings(_env_file=None)

        # llm_main_api_key가 우선
        assert settings.main_api_key == "sk-main-only"

    def test_main_api_key_missing_raises_error(self, monkeypatch):
        """Main API 키 누락 시 에러 발생"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_MAIN_API_KEY", raising=False)

        _get_cached_settings.cache_clear()
        settings = Settings(_env_file=None)

        with pytest.raises(ValueError, match="Main LLM API key is required"):
            _ = settings.main_api_key

    def test_task_base_url_fallback(self, monkeypatch):
        """Task Base URL fallback 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_BASE_URL", "https://common.example.com")
        monkeypatch.delenv("LLM_TASK_BASE_URL", raising=False)

        _get_cached_settings.cache_clear()
        settings = Settings(_env_file=None)

        assert settings.task_base_url == "https://common.example.com"

    def test_mixed_providers(self, monkeypatch):
        """Main=OpenAI, Task=Azure 혼합 구성 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("LLM_TASK_API_KEY", "azure-key")
        monkeypatch.setenv("LLM_TASK_BASE_URL", "https://azure.example.com")

        _get_cached_settings.cache_clear()
        settings = Settings(_env_file=None)

        assert settings.main_api_key == "sk-openai"
        assert settings.main_base_url is None
        assert settings.task_api_key == "azure-key"
        assert settings.task_base_url == "https://azure.example.com"
