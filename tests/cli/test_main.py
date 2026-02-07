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
    assert "--message" in result.stdout  # Option으로 표시되는지 확인


def test_cli_default_message():
    """기본 메시지로 실행 테스트 (인자 없음)"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--message" in result.stdout


def test_cli_custom_message():
    """커스텀 메시지로 실행 테스트"""
    result = runner.invoke(app, ["--message", "커스텀 회의", "--help"])
    assert result.exit_code == 0


def test_cli_no_stream_option():
    """--no-stream 옵션 존재 확인"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--no-stream" in result.stdout
