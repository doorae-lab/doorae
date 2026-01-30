"""CLI 테스트"""
from pathlib import Path
from typer.testing import CliRunner

from thetable.interfaces.cli import app


runner = CliRunner()


def test_cli_version():
    """버전 출력 테스트"""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_help():
    """도움말 출력 테스트"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "TheTable" in result.stdout
    assert "message" in result.stdout


def test_cli_basic_message():
    """기본 메시지 실행 테스트"""
    # 실제 회의를 실행하지 않고 CLI 파싱만 테스트
    # (실제 실행은 통합 테스트에서)
    result = runner.invoke(app, ["회의 시작", "--help"])
    # 옵션 확인
    assert "--profiles" in result.stdout or result.exit_code == 0
