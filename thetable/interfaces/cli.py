#!/usr/bin/env python3
"""Doorae/TheTable CLI entrypoints."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from thetable import __version__
from thetable.config import Settings, get_settings, setup_tracing
from thetable.graph.constants import STATUS_EMOJI
from thetable.interfaces.engine import MeetingEngine
from thetable.interfaces.event_utils import random_speaker_color
from thetable.interfaces.logging import setup_logging
from thetable.interfaces.time_utils import format_elapsed

DEFAULT_MESSAGE = "회의를 시작합니다"
console = Console()


def should_use_tui(no_tui_flag: bool) -> bool:
    """TUI 모드 사용 여부를 결정한다.

    Returns True only when: TTY detected AND terminal >= 80x24 AND --no-tui not set.
    """
    if no_tui_flag:
        return False
    if not sys.stdout.isatty():
        return False
    try:
        cols, rows = os.get_terminal_size()
        if cols < 80 or rows < 24:
            logger.warning(f"Terminal too small for TUI ({cols}x{rows}), falling back to CLI")
            return False
    except OSError:
        return False
    return True


class CliMeetingCallback:
    """Rich console adapter for MeetingEngine events."""

    def __init__(self, start_time: float, hide_delegated: bool = False) -> None:
        self._start_time = start_time
        self._hide_delegated = hide_delegated
        self._current_speaker: str | None = None
        self._current_delegated_speaker: str | None = None
        self._speaker_colors: dict[str, str] = {}
        self._prev_agenda_state: tuple[int, tuple[tuple[str, str], ...]] | None = None

    def _get_speaker_color(self, speaker: str) -> str:
        if speaker not in self._speaker_colors:
            self._speaker_colors[speaker] = random_speaker_color()
        return self._speaker_colors[speaker]

    async def on_raw_event(self, event: dict) -> None:
        _ = event

    async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None:
        if is_delegated:
            if self._hide_delegated or speaker == self._current_delegated_speaker:
                return
            self._current_delegated_speaker = speaker
            console.print(f"\n  [dim]↳ {speaker} (위임)[/dim]")
            return

        self._current_delegated_speaker = None
        if speaker == self._current_speaker:
            return
        if self._current_speaker:
            console.print()
        color = self._get_speaker_color(speaker)
        console.print(f"\n[bold {color}][{speaker}][/bold {color}]")
        self._current_speaker = speaker

    async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None:
        _ = speaker
        if is_delegated:
            if not self._hide_delegated:
                console.print(f"  [dim]{content}[/dim]", end="")
            return
        console.print(content, end="")

    async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None:
        _ = speaker
        if is_delegated:
            self._current_delegated_speaker = None
            if not self._hide_delegated:
                console.print()
            return
        console.print()
        console.rule(style="dim")

    async def on_human_turn_started(self, username: str) -> None:
        _ = username

    async def on_agenda_updated(self, agendas: list[dict], current_idx: int) -> None:
        current_state = (
            current_idx,
            tuple(
                (
                    str(agenda.get("title", "")),
                    str(agenda.get("status", "")),
                )
                for agenda in agendas
            ),
        )
        if current_state == self._prev_agenda_state:
            return
        self._prev_agenda_state = current_state
        console.print(format_agenda_panel(agendas, current_idx, self._start_time))
        console.print()

    async def on_meeting_ended(
        self,
        agendas: list[dict],
        speaker_counts: dict[str, int],
    ) -> None:
        _print_summary_table(agendas, speaker_counts)

    async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None:
        if pending_speakers:
            console.print(f"[dim]다음 발언 예정: {', '.join(pending_speakers)}[/dim]")

    async def on_participant_status_changed(self, participant_name: str, status: str) -> None:
        _ = (participant_name, status)

    async def on_tool_call(self, name: str, status: str) -> None:
        _ = (name, status)


def _print_summary_table(agendas: Optional[List[dict]], speaker_counts: Optional[dict]) -> None:
    """회의 요약 테이블 출력

    Args:
        agendas: 안건 리스트 (optional)
        speaker_counts: 발언 횟수 딕셔너리 (optional)
    """
    if not agendas and not speaker_counts:
        return

    table = Table(title="회의 요약", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("값", style="yellow")

    if agendas:
        completed = sum(1 for agenda in agendas if agenda["status"] == "completed")
        table.add_row("완료된 안건", f"{completed}/{len(agendas)}")

    if speaker_counts:
        for speaker, count in speaker_counts.items():
            table.add_row(f"{speaker} 발언 횟수", str(count))

    console.print("\n")
    console.print(table)


def format_agenda_panel(
    agendas: List[dict],
    current_idx: int,
    start_time: float,
) -> Panel:
    """안건 상태를 Rich Panel로 포맷팅."""
    lines = []

    for i, agenda in enumerate(agendas):
        status_emoji = STATUS_EMOJI.get(agenda["status"], "❓")
        owner = agenda.get("required_speakers", [""])[0] if agenda.get("required_speakers") else ""

        time_str = ""
        if agenda["status"] == "in_progress":
            agenda_start = agenda.get("start_time") or start_time
            elapsed = time.time() - agenda_start
            time_str = f" [{format_elapsed(max(0, int(elapsed)))}]"
        elif agenda["status"] == "completed":
            agenda_start = agenda.get("start_time")
            agenda_end = agenda.get("end_time")
            if agenda_start and agenda_end:
                elapsed = agenda_end - agenda_start
                time_str = f" [{format_elapsed(max(0, int(elapsed)))}]"

        indicator = " ← 현재" if i == current_idx else ""
        title = agenda["title"]
        lines.append(f"  {status_emoji} {i + 1}. {title} ({owner}){time_str}{indicator}")

        if agenda.get("decision"):
            lines.append(f"     └─ {agenda['decision']}")

    return Panel(
        "\n".join(lines),
        title="📋 안건 진행 상태",
        border_style="magenta",
    )


def _run_command_impl(
    *,
    message: str,
    profiles: Optional[Path],
    no_stream: bool,
    no_tui: bool,
    config: Optional[Path],
    verbose: bool,
    quiet: bool,
    trace: Optional[bool],
    hide_delegated: bool,
    app_title: str,
) -> None:
    use_tui = should_use_tui(no_tui)
    setup_logging(verbose=verbose, quiet=quiet, use_tui=use_tui)

    stream = not no_stream
    settings = get_settings(config_path=config)

    tracing_enabled = trace if trace is not None else settings.langchain_tracing_v2
    setup_tracing(
        enabled=tracing_enabled,
        api_key=settings.langchain_api_key,
        project=settings.langchain_project,
        endpoint=settings.langchain_endpoint,
    )

    logger.debug(f"Starting {app_title} CLI run")
    asyncio.run(
        run_meeting(
            initial_message=message,
            profiles_path=profiles,
            stream=stream,
            settings=settings,
            use_tui=use_tui,
            hide_delegated=hide_delegated,
            app_title=app_title,
        )
    )


def _not_implemented(command_name: str) -> None:
    typer.echo(f"`{command_name}` 명령은 예정되어 있지만 아직 구현되지 않았습니다.")
    raise typer.Exit(code=1)


def _build_cli_app(command_name: str, display_name: str) -> typer.Typer:
    cli = typer.Typer(
        name=command_name,
        help=f"{display_name} - AI-powered team meeting system",
        add_completion=False,
    )
    project_app = typer.Typer(help=f"{display_name} 프로젝트 관리")
    cli.add_typer(project_app, name="project")

    @cli.callback(invoke_without_command=True)
    def root(
        ctx: typer.Context,
        message: str = typer.Option(DEFAULT_MESSAGE, "--message", "-m", help="회의 시작 메시지"),
        profiles: Optional[Path] = typer.Option(
            None,
            "--profiles",
            "-p",
            help="Agent 프로필 YAML 파일 경로",
            exists=True,
            dir_okay=False,
        ),
        no_stream: bool = typer.Option(False, "--no-stream", help="스트리밍 모드 비활성화 (배치 모드 사용)"),
        no_tui: bool = typer.Option(False, "--no-tui", help="TUI 모드 비활성화 (클래식 CLI 출력 사용)"),
        config: Optional[Path] = typer.Option(
            None,
            "--config",
            "-c",
            help=".env 설정 파일 경로",
            exists=True,
            dir_okay=False,
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 출력 (DEBUG 레벨)"),
        quiet: bool = typer.Option(False, "--quiet", "-q", help="최소 출력 (WARNING 레벨만)"),
        version: bool = typer.Option(False, "--version", "-V", help="버전 정보 출력"),
        trace: Optional[bool] = typer.Option(None, "--trace", "-t", help="LangSmith 추적 활성화"),
        hide_delegated: bool = typer.Option(False, "--hide-delegated", help="서브 에이전트(위임) 발언 숨김 (CLI 모드)"),
    ) -> None:
        if version:
            console.print(f"{display_name} version: {__version__}")
            raise typer.Exit(code=0)
        if ctx.invoked_subcommand is not None:
            return
        _run_command_impl(
            message=message,
            profiles=profiles,
            no_stream=no_stream,
            no_tui=no_tui,
            config=config,
            verbose=verbose,
            quiet=quiet,
            trace=trace,
            hide_delegated=hide_delegated,
            app_title=display_name,
        )

    @cli.command("run", help="설정된 회의 워크플로우 실행")
    def run_command(
        message: str = typer.Option(DEFAULT_MESSAGE, "--message", "-m", help="회의 시작 메시지"),
        profiles: Optional[Path] = typer.Option(
            None,
            "--profiles",
            "-p",
            help="Agent 프로필 YAML 파일 경로",
            exists=True,
            dir_okay=False,
        ),
        no_stream: bool = typer.Option(False, "--no-stream", help="스트리밍 모드 비활성화 (배치 모드 사용)"),
        no_tui: bool = typer.Option(False, "--no-tui", help="TUI 모드 비활성화 (클래식 CLI 출력 사용)"),
        config: Optional[Path] = typer.Option(
            None,
            "--config",
            "-c",
            help=".env 설정 파일 경로",
            exists=True,
            dir_okay=False,
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 출력 (DEBUG 레벨)"),
        quiet: bool = typer.Option(False, "--quiet", "-q", help="최소 출력 (WARNING 레벨만)"),
        trace: Optional[bool] = typer.Option(None, "--trace", "-t", help="LangSmith 추적 활성화"),
        hide_delegated: bool = typer.Option(False, "--hide-delegated", help="서브 에이전트(위임) 발언 숨김 (CLI 모드)"),
    ) -> None:
        _run_command_impl(
            message=message,
            profiles=profiles,
            no_stream=no_stream,
            no_tui=no_tui,
            config=config,
            verbose=verbose,
            quiet=quiet,
            trace=trace,
            hide_delegated=hide_delegated,
            app_title=display_name,
        )

    @cli.command("init", help="로컬 워크스페이스 초기화 (예정)")
    def init_command(
        force: bool = typer.Option(False, "--force", help="기존 워크스페이스가 있으면 덮어씁니다."),
    ) -> None:
        _ = force
        _not_implemented(f"{command_name} init")

    @project_app.command("create", help="새 프로젝트 스캐폴드를 생성합니다 (예정)")
    def project_create_command(
        name: str = typer.Argument(..., help="프로젝트 이름"),
        slug: Optional[str] = typer.Option(None, "--slug", help="명시적으로 사용할 프로젝트 슬러그"),
        template: str = typer.Option("default", "--template", help="프로젝트 템플릿 이름"),
        mcp: Optional[List[str]] = typer.Option(None, "--mcp", help="프로젝트 설정에 기록할 MCP 서버"),
        set_current: bool = typer.Option(False, "--set-current", help="새 프로젝트를 현재 워크스페이스 프로젝트로 설정합니다."),
    ) -> None:
        _ = (name, slug, template, mcp, set_current)
        _not_implemented(f"{command_name} project create")

    return cli


doorae_app = _build_cli_app(command_name="doorae", display_name="Doorae")
app = _build_cli_app(command_name="thetable", display_name="TheTable")
legacy_app = app


def doorae_main() -> None:
    """Run the primary Doorae CLI entrypoint."""
    doorae_app()


def thetable_main() -> None:
    """Run the legacy TheTable CLI entrypoint."""
    app()


async def _initialize_mcp(settings: Settings, use_tui: bool = False) -> dict[str, list] | None:
    """MCP 도구 초기화

    Args:
        settings: Settings 인스턴스
        use_tui: TUI 모드 여부 (True면 console 출력 억제)

    Returns:
        서버별 MCP 도구 딕셔너리 또는 None
    """
    logger.debug("Initializing MCP tools...")
    from thetable.graph.workflow import initialize_mcp_tools

    try:
        mcp_tools = await initialize_mcp_tools()
        if mcp_tools:
            total = sum(len(tools) for tools in mcp_tools.values())
            logger.info(f"MCP 도구 로드 완료: {total}개 도구 ({len(mcp_tools)}개 서버)")
            if not use_tui:
                console.print(f"[green]✅ MCP 도구 로드 완료: {total}개 도구 ({len(mcp_tools)}개 서버)[/green]")
        else:
            logger.warning("MCP 도구를 사용할 수 없습니다")
            if not use_tui:
                console.print("[yellow]⚠️  MCP 도구를 사용할 수 없습니다[/yellow]")
                console.print("[yellow]   확인 사항:[/yellow]")
                console.print("[yellow]   1. config/mcp_servers.json 파일 존재 여부[/yellow]")
                console.print("[yellow]   2. .env 파일의 GITHUB_PERSONAL_ACCESS_TOKEN 설정 여부[/yellow]")
        return mcp_tools
    except Exception as exc:
        logger.warning(f"MCP 초기화 실패: {exc}")
        if not use_tui:
            console.print(f"[yellow]⚠️  MCP 초기화 실패: {exc}[/yellow]")
            console.print("[yellow]   확인 사항:[/yellow]")
            console.print("[yellow]   1. config/mcp_servers.json 파일 존재 여부[/yellow]")
            console.print("[yellow]   2. .env 파일의 GITHUB_PERSONAL_ACCESS_TOKEN 설정 여부[/yellow]")
        return None


async def _run_streaming(engine: MeetingEngine, hide_delegated: bool = False) -> None:
    """스트리밍 모드 실행

    Args:
        engine: 공통 MeetingEngine 인스턴스
        hide_delegated: 위임 발언 숨김 여부
    """
    setup_state = engine.setup_state or engine.setup()
    raw_start_time = setup_state.initial_state.get("start_time")
    start_time = float(raw_start_time) if isinstance(raw_start_time, (int, float)) else time.time()
    callback = CliMeetingCallback(start_time=start_time, hide_delegated=hide_delegated)
    await engine.run(callback)


async def _run_batch(workflow, state: dict, config: dict) -> dict:
    """배치 모드 실행

    Args:
        workflow: 워크플로우 인스턴스
        state: 초기 상태
        config: LangGraph 설정

    Returns:
        실행 결과 딕셔너리
    """
    logger.debug("Invoking workflow...")
    result = await workflow.ainvoke(state, config=config)
    logger.debug(f"Workflow completed. Result keys: {result.keys()}")

    console.print("\n[bold]📝 회의 기록[/bold]")
    console.rule(style="yellow")

    speaker_colors: dict[str, str] = {}

    for msg in result.get("messages", []):
        speaker = getattr(msg, "name", "System")
        if speaker not in speaker_colors:
            speaker_colors[speaker] = random_speaker_color()
        color = speaker_colors[speaker]

        console.print(f"\n[bold {color}][{speaker}][/bold {color}]")
        console.print(msg.content)
        console.rule(style="dim")

    _print_summary_table(result.get("agendas"), result.get("speaker_counts"))

    return result


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[Path] = None,
    stream: bool = False,
    settings: Optional[Settings] = None,
    use_tui: bool = False,
    hide_delegated: bool = False,
    app_title: str = "TheTable",
) -> None:
    """회의 실행.

    Args:
        initial_message: 회의 시작 메시지
        profiles_path: agent_profiles.yaml 경로 (None이면 설정값 사용)
        stream: 스트리밍 모드 사용 여부
        settings: Settings 인스턴스 (None이면 기본 설정 사용)
        use_tui: TUI 모드 여부 (True면 stderr를 로그 파일로 리다이렉트)
        hide_delegated: 위임 발언 숨김 여부
        app_title: 사용자에게 보여줄 CLI 이름
    """
    if settings is None:
        settings = get_settings()

    if profiles_path is None:
        profiles_path = Path(settings.agent_profiles_path)

    if not use_tui:
        console.print(
            Panel(
                f"[bold]회의 시작[/bold]\n\n"
                f"프로필: [cyan]{profiles_path}[/cyan]\n"
                f"Main LLM: [yellow]{settings.llm_main_model}[/yellow] "
                f"(온도: {settings.llm_main_temperature})\n"
                f"Task LLM: [yellow]{settings.llm_task_model}[/yellow] "
                f"(온도: {settings.llm_task_temperature})",
                title=f"🚀 {app_title}",
                border_style="green",
            )
        )

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    stderr_backup = None
    stderr_file = None
    if use_tui:
        stderr_backup = sys.stderr
        stderr_file = open("thetable.log", "a")
        sys.stderr = stderr_file

    try:
        mcp_tools = await _initialize_mcp(settings, use_tui=use_tui)

        if use_tui:
            from thetable.interfaces.tui import MeetingTuiApp

            tui_app = MeetingTuiApp(
                settings=settings,
                profiles_path=str(profiles_path),
                initial_message=initial_message,
                mcp_tools=mcp_tools,
            )
            await tui_app.run_async()
            return

        engine = MeetingEngine(
            initial_message=initial_message,
            settings=settings,
            profiles_path=str(profiles_path),
            mcp_tools=mcp_tools or {},
        )
        setup_state = engine.setup()
        logger.debug(f"Workflow created: {setup_state.workflow}")
        logger.debug(f"Human participants: {setup_state.human_names}")
        logger.debug(f"Initial state: {setup_state.initial_state}")
        logger.debug(f"Running workflow (stream={stream})...")

        if stream:
            await _run_streaming(engine, hide_delegated=hide_delegated)
        else:
            await _run_batch(
                setup_state.workflow,
                setup_state.initial_state,
                setup_state.graph_config,
            )

        console.print(
            Panel(
                "[bold green]회의 종료[/bold green]",
                border_style="green",
            )
        )
    finally:
        if stderr_backup is not None:
            sys.stderr = stderr_backup
        if stderr_file is not None:
            stderr_file.close()


if __name__ == "__main__":
    thetable_main()
