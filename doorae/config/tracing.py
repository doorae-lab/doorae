"""LangSmith 추적 설정 모듈"""
import os
from typing import Optional

from loguru import logger


def setup_tracing(
    enabled: bool,
    api_key: Optional[str] = None,
    project: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> bool:
    """LangSmith 추적 설정.

    Args:
        enabled: 추적 활성화 여부
        api_key: LangSmith API 키
        project: LangSmith 프로젝트 이름
        endpoint: LangSmith 엔드포인트 URL

    Returns:
        bool: 추적이 성공적으로 설정되었는지 여부
    """
    if not enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        logger.debug("LangSmith tracing disabled")
        return False

    if not api_key:
        logger.warning(
            "LangSmith tracing enabled but LANGCHAIN_API_KEY is not set. "
            "Tracing will not work."
        )
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = api_key

    if project:
        os.environ["LANGCHAIN_PROJECT"] = project

    if endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = endpoint

    logger.info(f"LangSmith tracing enabled (project: {project or 'default'})")
    return True
