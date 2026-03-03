"""LLM 인스턴스 팩토리"""

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from thetable.config.settings import Settings, get_settings
from thetable.core.profile import AgentProfile


def create_main_llm(streaming: bool = False) -> BaseChatModel:
    """Main LLM 인스턴스 생성

    Args:
        streaming: 스트리밍 활성화 여부

    Returns:
        ChatOpenAI 인스턴스
    """
    settings = get_settings()
    kwargs = {
        "model": settings.llm_main_model,
        "temperature": settings.llm_main_temperature,
        "max_tokens": settings.llm_main_max_tokens,
        "api_key": settings.main_api_key,
        "timeout": settings.llm_timeout,
        "max_retries": settings.llm_max_retries,
    }
    if streaming:
        kwargs["streaming"] = True
    if settings.main_base_url:
        kwargs["base_url"] = settings.main_base_url
    return ChatOpenAI(**kwargs)


def create_task_llm() -> BaseChatModel:
    """Task LLM 인스턴스 생성

    Returns:
        ChatOpenAI 인스턴스
    """
    settings = get_settings()
    kwargs = {
        "model": settings.llm_task_model,
        "temperature": settings.llm_task_temperature,
        "max_tokens": settings.llm_task_max_tokens,
        "api_key": settings.task_api_key,
        "timeout": settings.llm_timeout,
        "max_retries": settings.llm_max_retries,
    }
    if settings.task_base_url:
        kwargs["base_url"] = settings.task_base_url
    return ChatOpenAI(**kwargs)


def create_agent_llm(
    profile: AgentProfile,
    settings: Optional[Settings] = None,
    streaming: bool = False,
) -> BaseChatModel:
    """에이전트별 LLM 인스턴스 생성

    Args:
        profile: 에이전트 프로필
        settings: 글로벌 설정 (None이면 get_settings() 사용)
        streaming: 스트리밍 활성화 여부

    Returns:
        ChatOpenAI 인스턴스
    """
    resolved_settings = settings or get_settings()
    llm_config = profile.llm

    kwargs = {
        "model": llm_config.model if llm_config and llm_config.model else resolved_settings.llm_main_model,
        "temperature": (
            llm_config.temperature
            if llm_config and llm_config.temperature is not None
            else resolved_settings.llm_main_temperature
        ),
        "max_tokens": (
            llm_config.max_tokens
            if llm_config and llm_config.max_tokens is not None
            else resolved_settings.llm_main_max_tokens
        ),
        "api_key": llm_config.api_key if llm_config and llm_config.api_key else resolved_settings.main_api_key,
        "timeout": resolved_settings.llm_timeout,
        "max_retries": resolved_settings.llm_max_retries,
    }

    if streaming:
        kwargs["streaming"] = True

    base_url = llm_config.base_url if llm_config and llm_config.base_url else resolved_settings.main_base_url
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)
