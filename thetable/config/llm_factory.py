"""LLM 인스턴스 팩토리"""

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from thetable.config.settings import get_settings


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
