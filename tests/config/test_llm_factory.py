"""LLM 팩토리 테스트"""

import pytest
from unittest.mock import patch, MagicMock
from thetable.config.llm_factory import create_main_llm, create_task_llm


@pytest.fixture
def mock_settings():
    """모의 설정 객체"""
    settings = MagicMock()
    settings.llm_main_model = "gpt-4o-mini"
    settings.llm_main_temperature = 0.7
    settings.llm_main_max_tokens = 4000
    settings.main_api_key = "test-main-key"
    settings.main_base_url = None
    settings.llm_timeout = 30
    settings.llm_max_retries = 2

    settings.llm_task_model = "gpt-4o-mini"
    settings.llm_task_temperature = 0.0
    settings.llm_task_max_tokens = 2000
    settings.task_api_key = "test-task-key"
    settings.task_base_url = None

    return settings


def test_create_main_llm_default(mock_settings):
    """Main LLM 기본 생성 테스트"""
    with patch("thetable.config.llm_factory.get_settings", return_value=mock_settings):
        with patch("thetable.config.llm_factory.ChatOpenAI") as mock_chat:
            create_main_llm()

            # ChatOpenAI 호출 확인
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]

            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 4000
            assert call_kwargs["api_key"] == "test-main-key"
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["max_retries"] == 2
            assert "streaming" not in call_kwargs


def test_create_main_llm_with_streaming(mock_settings):
    """Main LLM 스트리밍 활성화 테스트"""
    with patch("thetable.config.llm_factory.get_settings", return_value=mock_settings):
        with patch("thetable.config.llm_factory.ChatOpenAI") as mock_chat:
            create_main_llm(streaming=True)

            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["streaming"] is True


def test_create_main_llm_with_base_url(mock_settings):
    """Main LLM base_url 설정 테스트"""
    mock_settings.main_base_url = "https://custom.api.com"

    with patch("thetable.config.llm_factory.get_settings", return_value=mock_settings):
        with patch("thetable.config.llm_factory.ChatOpenAI") as mock_chat:
            create_main_llm()

            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["base_url"] == "https://custom.api.com"


def test_create_task_llm(mock_settings):
    """Task LLM 생성 테스트"""
    with patch("thetable.config.llm_factory.get_settings", return_value=mock_settings):
        with patch("thetable.config.llm_factory.ChatOpenAI") as mock_chat:
            create_task_llm()

            # ChatOpenAI 호출 확인
            mock_chat.assert_called_once()
            call_kwargs = mock_chat.call_args[1]

            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["temperature"] == 0.0
            assert call_kwargs["max_tokens"] == 2000
            assert call_kwargs["api_key"] == "test-task-key"
            assert call_kwargs["timeout"] == 30
            assert call_kwargs["max_retries"] == 2


def test_create_task_llm_with_base_url(mock_settings):
    """Task LLM base_url 설정 테스트"""
    mock_settings.task_base_url = "https://task.api.com"

    with patch("thetable.config.llm_factory.get_settings", return_value=mock_settings):
        with patch("thetable.config.llm_factory.ChatOpenAI") as mock_chat:
            create_task_llm()

            call_kwargs = mock_chat.call_args[1]
            assert call_kwargs["base_url"] == "https://task.api.com"
