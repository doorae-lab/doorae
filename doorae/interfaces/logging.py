"""로깅 설정 모듈"""
import sys
from loguru import logger


def setup_logging(verbose: bool = False, quiet: bool = False, use_tui: bool = False) -> None:
    """로깅 설정.
    Args:
        verbose: 상세 출력 모드 (DEBUG 레벨)
        quiet: 최소 출력 모드 (WARNING 레벨만)
        use_tui: TUI 모드 시 파일로 리다이렉트
    """
    # 기존 핸들러 제거
    logger.remove()
    if verbose:
        level = "DEBUG"
    elif quiet:
        level = "WARNING"
    else:
        level = "INFO"
    if use_tui:
        logger.add(
            "doorae.log",
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="1 MB",
        )
        return

    # CLI 모드: stderr 출력
    if verbose:
        format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    elif quiet:
        format_str = "<level>{level}: {message}</level>"
    else:
        format_str = "<level>{level: <8}</level> | <level>{message}</level>"
    logger.add(
        sys.stderr,
        level=level,
        format=format_str,
        colorize=True,
    )
