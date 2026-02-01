"""LangSmith 추적 설정 테스트"""
import os

import pytest

from thetable.config.tracing import setup_tracing


class TestSetupTracing:
    """setup_tracing 함수 테스트"""

    def teardown_method(self):
        """테스트 후 환경변수 정리"""
        for key in [
            "LANGCHAIN_TRACING_V2",
            "LANGCHAIN_API_KEY",
            "LANGCHAIN_PROJECT",
            "LANGCHAIN_ENDPOINT",
        ]:
            os.environ.pop(key, None)

    def test_disabled_tracing(self):
        """비활성화 시 환경변수 설정"""
        result = setup_tracing(enabled=False)

        assert result is False
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"

    def test_enabled_without_api_key(self):
        """API 키 없이 활성화 시 경고"""
        result = setup_tracing(enabled=True, api_key=None)

        assert result is False
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"

    def test_enabled_with_api_key(self):
        """API 키와 함께 활성화"""
        result = setup_tracing(
            enabled=True, api_key="test-api-key", project="test-project"
        )

        assert result is True
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_API_KEY") == "test-api-key"
        assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"

    def test_optional_endpoint(self):
        """엔드포인트 설정"""
        setup_tracing(
            enabled=True,
            api_key="test-key",
            endpoint="https://custom.endpoint.com",
        )

        assert os.environ.get("LANGCHAIN_ENDPOINT") == "https://custom.endpoint.com"
