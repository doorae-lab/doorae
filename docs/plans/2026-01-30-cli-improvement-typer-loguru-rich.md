# CLI 개선: Typer + loguru + Rich 전환

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** argparse 기반 CLI를 Typer로 전환하고, loguru/Rich를 도입하여 사용자 경험을 개선

**Architecture:** Typer를 사용한 선언적 CLI 구조, loguru를 통한 구조화된 로깅, Rich를 통한 향상된 터미널 UI

**Tech Stack:** Typer 0.12+, loguru 0.7+, Rich 13+, pydantic-settings 2.0+

---

## Task 1: 의존성 추가 및 버전 확인

**Files:**
- Modify: `pyproject.toml`
- Verify: `thetable/__init__.py`

**Step 1: 의존성 추가**

```bash
uv add typer loguru rich
```

**Step 2: 버전 정보 확인**

파일: `thetable/__init__.py`

현재 버전이 이미 정의되어 있는지 확인:
```python
__version__ = "0.1.0"
```

이미 존재하면 이 단계 스킵.

**Step 3: pyproject.toml 검증**

Run: `cat pyproject.toml | grep -A 5 dependencies`
Expected: typer, loguru, rich가 dependencies에 포함되어 있어야 함

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add typer, loguru, rich dependencies"
```

---

## Task 2: 로깅 설정 모듈 생성

**Files:**
- Create: `thetable/interfaces/logging.py`
- Test: `tests/interfaces/test_logging.py`

**Step 1: 테스트 디렉토리 생성**

```bash
mkdir -p tests/interfaces
touch tests/interfaces/__init__.py
```

**Step 2: 로깅 설정 테스트 작성**

파일: `tests/interfaces/test_logging.py`

```python
"""로깅 설정 테스트"""
import sys
from io import StringIO
from loguru import logger

from thetable.interfaces.logging import setup_logging


def test_setup_logging_verbose():
    """verbose 모드 테스트"""
    # 기존 핸들러 제거
    logger.remove()

    # StringIO로 출력 캡처
    output = StringIO()
    logger.add(output, level="DEBUG")

    setup_logging(verbose=True, quiet=False)

    # DEBUG 레벨 메시지가 출력되는지 확인
    logger.debug("test message")
    assert "test message" in output.getvalue()


def test_setup_logging_quiet():
    """quiet 모드 테스트"""
    logger.remove()

    output = StringIO()
    logger.add(output, level="WARNING")

    setup_logging(verbose=False, quiet=True)

    # INFO 레벨 메시지가 출력되지 않아야 함
    logger.info("test info")
    assert "test info" not in output.getvalue()

    # WARNING은 출력되어야 함
    logger.warning("test warning")
    assert "test warning" in output.getvalue()


def test_setup_logging_default():
    """기본 모드 테스트"""
    logger.remove()

    output = StringIO()
    logger.add(output, level="INFO")

    setup_logging(verbose=False, quiet=False)

    # INFO 레벨 메시지가 출력되어야 함
    logger.info("test info")
    assert "test info" in output.getvalue()
```

**Step 3: 테스트 실행 (실패 확인)**

Run: `uv run pytest tests/interfaces/test_logging.py -v`
Expected: FAIL - "ModuleNotFoundError: No module named 'thetable.interfaces.logging'"

**Step 4: 로깅 모듈 구현**

파일: `thetable/interfaces/logging.py`

```python
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
```

**Step 5: 테스트 실행 (성공 확인)**

Run: `uv run pytest tests/interfaces/test_logging.py -v`
Expected: PASS (3/3 tests)

**Step 6: Commit**

```bash
git add thetable/interfaces/logging.py tests/interfaces/
git commit -m "feat: add logging configuration module with loguru"
```

---

## Task 3: Settings에 커스텀 경로 지원 추가

**Files:**
- Modify: `thetable/config/settings.py`
- Test: `tests/config/test_settings.py`

**Step 1: 테스트 파일 확인 및 테스트 추가**

파일: `tests/config/test_settings.py`

기존 테스트 파일이 있다면 추가, 없다면 생성:

```python
"""Settings 테스트"""
import os
from pathlib import Path
import tempfile

from thetable.config.settings import get_settings


def test_get_settings_default():
    """기본 설정 로드 테스트"""
    settings = get_settings()
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_temperature == 0.7


def test_get_settings_custom_path():
    """커스텀 경로 설정 파일 로드 테스트"""
    # 임시 .env 파일 생성
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("OPENAI_API_KEY=test-custom-key\n")
        f.write("LLM_MODEL=gpt-4o\n")
        f.write("LLM_TEMPERATURE=0.9\n")
        temp_path = f.name

    try:
        # 커스텀 경로로 설정 로드
        settings = get_settings(config_path=Path(temp_path))

        assert settings.openai_api_key == "test-custom-key"
        assert settings.llm_model == "gpt-4o"
        assert settings.llm_temperature == 0.9
    finally:
        # 임시 파일 삭제
        os.unlink(temp_path)
```

**Step 2: 테스트 실행 (실패 확인)**

Run: `uv run pytest tests/config/test_settings.py::test_get_settings_custom_path -v`
Expected: FAIL - "TypeError: get_settings() got an unexpected keyword argument 'config_path'"

**Step 3: Settings 수정**

파일: `thetable/config/settings.py`

```python
from functools import lru_cache
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """중앙 집중식 설정 관리 클래스."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str  # 필수
    openai_base_url: Optional[str] = None  # 선택적 (기본: OpenAI 공식 엔드포인트)
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    agent_profiles_path: str = "config/agent_profiles.yaml"


def get_settings(config_path: Optional[Path] = None) -> Settings:
    """Settings 인스턴스 반환.

    Args:
        config_path: 커스텀 .env 파일 경로 (None이면 기본 .env 사용)

    Returns:
        Settings 인스턴스

    Note:
        config_path를 지정하면 lru_cache를 우회하고 매번 새 인스턴스 생성
    """
    if config_path is not None:
        # 커스텀 경로 사용 시 캐시 우회
        return Settings(_env_file=str(config_path))

    # 기본 경로 사용 시 캐싱된 인스턴스 반환
    return _get_cached_settings()


@lru_cache
def _get_cached_settings() -> Settings:
    """캐싱된 Settings 인스턴스 반환 (내부 사용)."""
    return Settings()
```

**Step 4: 테스트 실행 (성공 확인)**

Run: `uv run pytest tests/config/test_settings.py -v`
Expected: PASS (2/2 tests)

**Step 5: Commit**

```bash
git add thetable/config/settings.py tests/config/test_settings.py
git commit -m "feat: add custom config path support to Settings"
```

---

## Task 4: Typer 기반 CLI 재작성

**Files:**
- Modify: `thetable/interfaces/cli.py`
- Test: `tests/cli/test_main.py`

**Step 1: 기존 테스트 확인**

Run: `cat tests/cli/test_main.py`

기존 테스트가 있다면 구조 파악, 없다면 다음 단계로.

**Step 2: Typer 테스트 작성**

파일: `tests/cli/test_main.py`

```python
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
```

**Step 3: 테스트 실행 (실패 확인)**

Run: `uv run pytest tests/cli/test_main.py -v`
Expected: FAIL - "AttributeError: module 'thetable.interfaces.cli' has no attribute 'app'"

**Step 4: CLI 재작성**

파일: `thetable/interfaces/cli.py`

```python
#!/usr/bin/env python3
"""TheTable CLI - AI-powered team meeting system"""
import asyncio
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langchain_core.messages import HumanMessage

from thetable import __version__
from thetable.config import get_settings
from thetable.graph.workflow import create_meeting_workflow
from thetable.interfaces.logging import setup_logging


app = typer.Typer(
    name="thetable",
    help="TheTable - AI-powered team meeting system",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """버전 정보 출력"""
    if value:
        console.print(f"TheTable version: {__version__}")
        raise typer.Exit()


@app.command()
def main(
    message: str = typer.Argument(
        ...,
        help="회의 시작 메시지 (Host가 먼저 말할 내용)",
    ),
    profiles: Optional[Path] = typer.Option(
        None,
        "--profiles",
        "-p",
        help="Agent 프로필 YAML 파일 경로",
        exists=True,
        dir_okay=False,
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        "-s",
        help="스트리밍 모드 사용 (실시간 출력)",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help=".env 설정 파일 경로",
        exists=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="상세 출력 (DEBUG 레벨)",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="최소 출력 (WARNING 레벨만)",
    ),
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="버전 정보 출력",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """TheTable CLI - AI 기반 팀 회의 시스템

    Examples:

        # 기본 회의 실행

        thetable "오늘 회의를 시작하겠습니다"

        # 커스텀 프로필 사용

        thetable "회의 시작" --profiles config/custom_profiles.yaml

        # 스트리밍 모드

        thetable "회의 시작" --stream

        # 커스텀 설정 파일

        thetable "회의 시작" --config .env.dev
    """
    # 로깅 설정
    setup_logging(verbose=verbose, quiet=quiet)

    # 비동기 실행
    asyncio.run(run_meeting(
        initial_message=message,
        profiles_path=profiles,
        stream=stream,
        config_path=config,
    ))


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[Path] = None,
    stream: bool = False,
    config_path: Optional[Path] = None,
) -> None:
    """회의 실행.

    Args:
        initial_message: 회의 시작 메시지
        profiles_path: agent_profiles.yaml 경로 (None이면 설정값 사용)
        stream: 스트리밍 모드 사용 여부
        config_path: .env 파일 경로 (None이면 기본 .env 사용)
    """
    # 설정 로드
    settings = get_settings(config_path=config_path)

    # 프로필 경로 결정
    if profiles_path is None:
        profiles_path = Path(settings.agent_profiles_path)

    # 회의 시작 패널
    console.print(
        Panel(
            f"[bold]회의 시작[/bold]\n\n"
            f"프로필: [cyan]{profiles_path}[/cyan]\n"
            f"모델: [yellow]{settings.llm_model}[/yellow] "
            f"(온도: {settings.llm_temperature})",
            title="🚀 TheTable",
            border_style="green",
        )
    )

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    # Workflow 생성
    workflow = create_meeting_workflow(profiles_path=str(profiles_path))

    # 초기 상태
    initial_state = {
        "messages": [HumanMessage(content=initial_message)],
        "current_phase": "opening",
    }

    # 실행
    if stream:
        # 스트리밍 모드
        async for event in workflow.astream(initial_state):
            if "messages" in event:
                for msg in event["messages"]:
                    speaker = getattr(msg, "name", "System")
                    console.print(f"\n[bold cyan][{speaker}][/bold cyan]")
                    console.print(msg.content)
                    console.rule(style="dim")
    else:
        # 일반 모드
        result = await workflow.ainvoke(initial_state)

        # 결과 출력
        console.print("\n[bold]📝 회의 기록[/bold]")
        console.rule(style="yellow")

        for msg in result.get("messages", []):
            speaker = getattr(msg, "name", "System")
            # 에이전트별 색상
            color_map = {
                "Host": "green",
                "Analyst": "blue",
                "Critic": "red",
                "Optimizer": "yellow",
            }
            color = color_map.get(speaker, "white")

            console.print(f"\n[bold {color}][{speaker}][/bold {color}]")
            console.print(msg.content)
            console.rule(style="dim")

        # 메타 정보 테이블
        if "current_phase" in result or "speaker_counts" in result:
            table = Table(title="회의 요약", show_header=True)
            table.add_column("항목", style="cyan")
            table.add_column("값", style="yellow")

            if "current_phase" in result:
                table.add_row("최종 Phase", result["current_phase"])

            if "speaker_counts" in result:
                counts = result["speaker_counts"]
                for speaker, count in counts.items():
                    table.add_row(f"{speaker} 발언 횟수", str(count))

            console.print("\n")
            console.print(table)

    # 회의 종료 패널
    console.print(
        Panel(
            "[bold green]회의 종료[/bold green]",
            border_style="green",
        )
    )


if __name__ == "__main__":
    app()
```

**Step 5: 테스트 실행 (성공 확인)**

Run: `uv run pytest tests/cli/test_main.py -v`
Expected: PASS (3/3 tests)

**Step 6: CLI 실행 테스트**

Run: `uv run thetable --version`
Expected: "TheTable version: 0.1.0"

Run: `uv run thetable --help`
Expected: 도움말 출력

**Step 7: Commit**

```bash
git add thetable/interfaces/cli.py tests/cli/test_main.py
git commit -m "feat: rewrite CLI with Typer, loguru, and Rich

- Replace argparse with Typer for declarative CLI
- Add loguru for structured logging
- Add Rich for enhanced terminal UI
- Add --config, --verbose, --quiet, --version options
- Improve output formatting with panels and tables"
```

---

## Task 5: 통합 테스트 및 검증

**Files:**
- Test: All CLI functionality

**Step 1: 기본 실행 테스트**

Run: `uv run thetable "회의를 시작합니다"`
Expected: 회의가 정상적으로 실행되고 Rich 패널/테이블 출력

**Step 2: Verbose 모드 테스트**

Run: `uv run thetable "회의 시작" -v`
Expected: DEBUG 레벨 로그 출력, 상세한 정보 표시

**Step 3: Quiet 모드 테스트**

Run: `uv run thetable "회의 시작" -q`
Expected: WARNING 레벨만 출력, 최소한의 정보

**Step 4: 전체 테스트 실행**

Run: `uv run pytest -v`
Expected: 모든 테스트 PASS

**Step 5: 문서 확인 사항 정리**

다음 항목들이 정상 작동하는지 최종 확인:
- ✅ Typer 기반 CLI
- ✅ loguru 로깅
- ✅ Rich UI 출력
- ✅ 7개 옵션 (message, --profiles, --stream, --config, --verbose, --quiet, --version)
- ✅ 커스텀 설정 파일 지원
- ✅ 향상된 출력 포맷 (Panel, Table, 색상)

**Step 6: 최종 Commit**

```bash
git add .
git commit -m "docs: update CLI improvement implementation

- All tests passing
- CLI functionality verified
- Documentation updated"
```

---

## 완료 조건

1. ✅ 모든 테스트 통과 (`uv run pytest -v`)
2. ✅ CLI 명령어 정상 작동 (--help, --version, 기본 실행)
3. ✅ 7개 옵션 모두 동작 확인
4. ✅ loguru/Rich 출력 확인
5. ✅ if/for 깊이 2 depth 이하 유지
6. ✅ YAGNI/SOLID 원칙 준수
7. ✅ 중복 코드 없음

---

## 참고 사항

**CLAUDE.md 프로젝트 규칙:**
- uv 기반 실행 환경
- if/for문 깊이 2 depth 이하
- YAGNI 원칙 준수
- SOLID 원칙 준수
- 중복 코드 검토

**역할 분리:**
- **loguru**: 로깅/디버그 메시지
- **Rich**: 사용자 UI (Panel, Table, 색상)
- **CLI 옵션**: 런타임에 자주 바뀌는 것
- **config/.env**: 거의 안 바뀌는 설정
