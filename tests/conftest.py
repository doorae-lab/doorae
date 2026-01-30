import os
import pytest


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """모든 테스트에서 자동으로 환경 변수 설정."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    # Settings 캐시 초기화
    from thetable.config import get_settings
    get_settings.cache_clear()
