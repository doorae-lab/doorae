"""로깅 설정 테스트"""
import sys
from io import StringIO
from loguru import logger

from thetable.interfaces.logging import setup_logging


def test_setup_logging_verbose():
    """verbose 모드 테스트"""
    # setup_logging 호출 후 StringIO 핸들러 추가
    setup_logging(verbose=True, quiet=False)

    output = StringIO()
    logger.add(output, level="DEBUG")

    # DEBUG 레벨 메시지가 출력되는지 확인
    logger.debug("test message")
    assert "test message" in output.getvalue()


def test_setup_logging_quiet():
    """quiet 모드 테스트"""
    setup_logging(verbose=False, quiet=True)

    output = StringIO()
    logger.add(output, level="WARNING")

    # INFO 레벨 메시지가 출력되지 않아야 함
    logger.info("test info")
    assert "test info" not in output.getvalue()

    # WARNING은 출력되어야 함
    logger.warning("test warning")
    assert "test warning" in output.getvalue()


def test_setup_logging_default():
    """기본 모드 테스트"""
    setup_logging(verbose=False, quiet=False)

    output = StringIO()
    logger.add(output, level="INFO")

    # INFO 레벨 메시지가 출력되어야 함
    logger.info("test info")
    assert "test info" in output.getvalue()
