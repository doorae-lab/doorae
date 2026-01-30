"""로깅 설정 모듈"""
import sys
from loguru import logger


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """로깅 설정.

    Args:
        verbose: 상세 출력 모드 (DEBUG 레벨)
        quiet: 최소 출력 모드 (WARNING 레벨만)
    """
    # 기존 핸들러 제거
    logger.remove()

    # 로그 레벨 결정
    if verbose:
        level = "DEBUG"
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    elif quiet:
        level = "WARNING"
        format_str = "<level>{level}: {message}</level>"
    else:
        level = "INFO"
        format_str = "<level>{level: <8}</level> | <level>{message}</level>"

    # 핸들러 추가
    logger.add(
        sys.stderr,
        level=level,
        format=format_str,
        colorize=True,
    )
