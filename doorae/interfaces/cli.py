#!/usr/bin/env python3
"""Doorae CLI - AI-powered team meeting system."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
import typer
from loguru import logger
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from doorae import __version__
from doorae.config import Settings, get_settings, setup_tracing
from doorae.core.server_address import (
    ServerAddressParseError,
    parse_server_address,
)
from doorae.interfaces.event_utils import random_speaker_color
from doorae.interfaces.logging import setup_logging
from doorae.interfaces.time_utils import format_elapsed
from doorae.project import (
    ProjectRunContext,
    WorkspaceError,
    create_project,
    init_workspace,
    resolve_project_run,
)
from doorae.server.models import RoomInfo

if TYPE_CHECKING:
    from doorae.interfaces.engine import MeetingEngine


app = typer.Typer(
    name="doorae",
    help="Doorae - AI-powered team meeting system",
    add_completion=False,
)
project_app = typer.Typer(
    help="Manage workspace project scaffolds.",
    add_completion=False,
)
app.add_typer(project_app, name="project")
console = Console()
DEFAULT_MESSAGE = "회의를 시작합니다"
DEFAULT_SERVER_BIND = "0.0.0.0:8000"
DEFAULT_SERVER_EXAMPLE = "localhost:8000"
OPTIONAL_SERVER_DEPENDENCIES = {"fastapi", "starlette", "uvicorn"}


@dataclass(slots=True)
class ServerSessionConfig:
    room_id: str
    ws_url: str
    start_url: str


@dataclass(slots=True)
class CliRuntimeOptions:
    config: Path | None
    verbose: bool
    quiet: bool
    trace: bool | None


def _status_emoji(status: str) -> str:
    """Load agenda status icons lazily to keep help/version import-light."""
    from doorae.graph.constants import STATUS_EMOJI

    return STATUS_EMOJI.get(status, "?")


def should_use_tui(classic_flag: bool) -> bool:
    """Return whether the interactive TUI should be used."""
    if classic_flag:
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
    """Render a short end-of-meeting summary table."""
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
    """Format the agenda progress panel."""
    lines = []

    for index, agenda in enumerate(agendas):
        status_emoji = _status_emoji(agenda["status"])
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

        indicator = " ← 현재" if index == current_idx else ""
        line = f"  {status_emoji} {index + 1}. {agenda['title']} ({owner}){time_str}{indicator}"
        lines.append(line)

        if agenda.get("decision"):
            lines.append(f"     └─ {agenda['decision']}")

    return Panel(
        "\n".join(lines),
        title="📋 안건 진행 상태",
        border_style="magenta",
    )


def _run_default_command(
    *,
    message: str,
    profiles: Optional[Path],
    classic: bool,
    runtime_options: CliRuntimeOptions,
    version: bool,
    hide_delegated: bool,
) -> None:
    if version:
        console.print(f"Doorae version: {__version__}")
        raise typer.Exit(code=0)

    use_tui = should_use_tui(classic)
    settings = _configure_runtime(runtime_options=runtime_options, use_tui=use_tui)

    try:
        asyncio.run(
            run_meeting(
                initial_message=message,
                profiles_path=profiles,
                settings=settings,
                use_tui=use_tui,
                hide_delegated=hide_delegated,
            )
        )
    except RuntimeError as exc:
        console.print(f"[bold red]오류:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _get_runtime_options(ctx: typer.Context) -> CliRuntimeOptions:
    if isinstance(ctx.obj, CliRuntimeOptions):
        return ctx.obj
    return CliRuntimeOptions(config=None, verbose=False, quiet=False, trace=None)


def _configure_runtime(
    *,
    runtime_options: CliRuntimeOptions,
    use_tui: bool,
) -> Settings:
    setup_logging(
        verbose=runtime_options.verbose,
        quiet=runtime_options.quiet,
        use_tui=use_tui,
    )
    settings = get_settings(config_path=runtime_options.config)
    tracing_enabled = (
        runtime_options.trace
        if runtime_options.trace is not None
        else settings.langchain_tracing_v2
    )
    setup_tracing(
        enabled=tracing_enabled,
        api_key=settings.langchain_api_key,
        project=settings.langchain_project,
        endpoint=settings.langchain_endpoint,
    )
    return settings


def _build_project_runtime_settings(
    settings: Settings,
    project_run: ProjectRunContext,
) -> Settings:
    """Override runtime config paths from a resolved workspace project."""
    return settings.model_copy(
        update={
            "agent_profiles_path": str(project_run.profiles_path),
            "agendas_path": str(project_run.agendas_path),
        }
    )


def _run_project_command(
    *,
    project: str | None,
    message: str,
    classic: bool,
    runtime_options: CliRuntimeOptions,
    hide_delegated: bool,
) -> None:
    use_tui = should_use_tui(classic)
    settings = _configure_runtime(runtime_options=runtime_options, use_tui=use_tui)

    try:
        project_run = resolve_project_run(Path.cwd(), project=project)
        project_settings = _build_project_runtime_settings(settings, project_run)
        asyncio.run(
            run_meeting(
                initial_message=message,
                profiles_path=project_run.profiles_path,
                settings=project_settings,
                use_tui=use_tui,
                hide_delegated=hide_delegated,
            )
        )
    except WorkspaceError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except RuntimeError as exc:
        console.print(f"[bold red]?ㅻ쪟:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc


def _run_server_command(
    *,
    initial_message: str,
    profiles: Optional[Path],
    server: str,
    username: str,
    room_id: str | None,
    runtime_options: CliRuntimeOptions,
) -> None:
    settings = _configure_runtime(runtime_options=runtime_options, use_tui=True)
    try:
        asyncio.run(
            run_server_meeting(
                initial_message=initial_message,
                profiles_path=profiles,
                settings=settings,
                server_address=server,
                room_id=room_id,
                username=username,
            )
        )
    except RuntimeError as exc:
        _exit_with_runtime_error(exc)


def _exit_with_runtime_error(exc: RuntimeError) -> None:
    console.print(f"[bold red]오류:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


def _load_server_runner() -> Callable[[str], None]:
    """Load the server runtime lazily so the base CLI works without server extras."""
    try:
        from doorae.server import run_server
        from doorae.server.app import create_app
    except ImportError as exc:
        missing_module = (exc.name or "").split(".")[0]
        if missing_module in OPTIONAL_SERVER_DEPENDENCIES:
            typer.secho(
                "Server mode requires optional dependencies. Run 'uv sync --extra server'.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1) from exc
        raise

    _ = create_app
    return run_server


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    message: str = typer.Option(
        DEFAULT_MESSAGE,
        "--message",
        "-m",
        help="회의 시작 메시지",
    ),
    profiles: Optional[Path] = typer.Option(
        None,
        "--profiles",
        "-p",
        help="Agent 프로필 YAML 파일 경로",
        exists=True,
        dir_okay=False,
    ),
    classic: bool = typer.Option(
        False,
        "--classic",
        help="TUI 대신 클래식 CLI 출력 사용",
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
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="버전 정보 출력",
    ),
    trace: Optional[bool] = typer.Option(
        None,
        "--trace",
        "-t",
        help="LangSmith 추적 활성화",
    ),
    hide_delegated: bool = typer.Option(
        False,
        "--hide-delegated",
        help="서브 에이전트(위임) 발언 숨김 (CLI 모드)",
    ),
) -> None:
    """Doorae CLI - AI 기반 팀 회의 시스템."""
    runtime_options = CliRuntimeOptions(
        config=config,
        verbose=verbose,
        quiet=quiet,
        trace=trace,
    )
    ctx.obj = runtime_options

    if version and ctx.invoked_subcommand is None:
        console.print(f"Doorae version: {__version__}")
        raise typer.Exit(code=0)

    if ctx.invoked_subcommand is not None:
        return

    _run_default_command(
        message=message,
        profiles=profiles,
        classic=classic,
        runtime_options=runtime_options,
        version=version,
        hide_delegated=hide_delegated,
    )

@app.command("run")
def run_command(
    project: Optional[str] = typer.Option(
        None,
        "--project",
        help="Workspace project slug or project path to run",
    ),
    message: str = typer.Option(
        DEFAULT_MESSAGE,
        "--message",
        "-m",
        help="Meeting start message",
    ),
    classic: bool = typer.Option(
        False,
        "--classic",
        help="Use classic CLI output instead of TUI",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to a custom .env file",
        exists=True,
        dir_okay=False,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Reduce logging output",
    ),
    trace: Optional[bool] = typer.Option(
        None,
        "--trace",
        "-t",
        help="Enable LangSmith tracing",
    ),
    hide_delegated: bool = typer.Option(
        False,
        "--hide-delegated",
        help="Hide delegated sub-agent output in classic CLI mode",
    ),
) -> None:
    """Run a meeting using the current or selected workspace project."""
    runtime_options = CliRuntimeOptions(
        config=config,
        verbose=verbose,
        quiet=quiet,
        trace=trace,
    )
    _run_project_command(
        project=project,
        message=message,
        classic=classic,
        runtime_options=runtime_options,
        hide_delegated=hide_delegated,
    )


@app.command("create")
def create_command(
    ctx: typer.Context,
    username: str = typer.Option(
        "user",
        "--username",
        "-u",
        help="서버에서 표시할 사용자 이름",
    ),
    server: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        envvar="DOORAE_SERVER",
        help="접속할 서버 주소 (예: localhost:8000)",
    ),
    message: str = typer.Option(
        DEFAULT_MESSAGE,
        "--message",
        "-m",
        help="회의 시작 메시지",
    ),
    profiles: Optional[Path] = typer.Option(
        None,
        "--profiles",
        "-p",
        help="Agent 프로필 YAML 파일 경로",
        exists=True,
        dir_okay=False,
    ),
) -> None:
    """서버에 새 회의방을 만들고 바로 입장한다."""
    try:
        _run_server_command(
            initial_message=message,
            profiles=profiles,
            server=_require_server_address(server, command_name="create"),
            username=username,
            room_id=None,
            runtime_options=_get_runtime_options(ctx),
        )
    except RuntimeError as exc:
        _exit_with_runtime_error(exc)


@app.command("join")
def join_command(
    ctx: typer.Context,
    room_id: str = typer.Argument(..., metavar="ROOM_ID"),
    username: str = typer.Option(
        "user",
        "--username",
        "-u",
        help="서버에서 표시할 사용자 이름",
    ),
    server: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        envvar="DOORAE_SERVER",
        help="접속할 서버 주소 (예: localhost:8000)",
    ),
) -> None:
    """기존 회의방에 입장한다."""
    try:
        _run_server_command(
            initial_message=DEFAULT_MESSAGE,
            profiles=None,
            server=_require_server_address(server, command_name="join"),
            username=username,
            room_id=room_id,
            runtime_options=_get_runtime_options(ctx),
        )
    except RuntimeError as exc:
        _exit_with_runtime_error(exc)


@app.command("rooms")
def rooms_command(
    ctx: typer.Context,
    server: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        envvar="DOORAE_SERVER",
        help="조회할 서버 주소 (예: localhost:8000)",
    ),
) -> None:
    """서버의 회의방 목록을 조회한다."""
    runtime_options = _get_runtime_options(ctx)
    setup_logging(
        verbose=runtime_options.verbose,
        quiet=runtime_options.quiet,
        use_tui=False,
    )
    try:
        asyncio.run(_list_server_rooms(_require_server_address(server, command_name="rooms")))
    except RuntimeError as exc:
        _exit_with_runtime_error(exc)


@app.command("init")
def init_command(
    force: bool = typer.Option(
        False,
        "--force",
        help="기존 워크스페이스 메타데이터가 있으면 덮어씁니다.",
    ),
) -> None:
    """현재 디렉터리에 .doorae 워크스페이스를 초기화한다."""
    try:
        result = init_workspace(Path.cwd(), force=force)
    except WorkspaceError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    action = "Reinitialized" if result.already_existed else "Initialized"
    typer.secho(f"{action} Doorae workspace.", fg=typer.colors.GREEN)
    typer.echo(f"Workspace: {result.paths.workspace_dir}")
    typer.echo(f"Projects: {result.paths.projects_dir}")
    if result.copied_env_file:
        typer.echo("Created .env from the packaged template.")
    else:
        typer.echo("Kept existing .env.")


@project_app.command("create")
def project_create_command(
    name: str = typer.Argument(..., metavar="NAME"),
) -> None:
    """Create a scaffolded project inside the current workspace."""
    try:
        result = create_project(Path.cwd(), name)
    except WorkspaceError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho("Created Doorae project.", fg=typer.colors.GREEN)
    typer.echo(f"Project: {result.paths.project_dir}")
    typer.echo(f"Slug: {result.config.slug}")


@app.command("serve")
def serve_command(
    server: str = typer.Option(
        DEFAULT_SERVER_BIND,
        "--server",
        "-s",
        envvar="DOORAE_SERVER",
        help="바인딩할 서버 주소 (예: 0.0.0.0:8000)",
    ),
) -> None:
    """Doorae WebSocket 서버를 시작한다."""
    run_server = _load_server_runner()
    run_server(server)


async def _initialize_mcp(settings: Settings, use_tui: bool = False) -> dict[str, list] | None:
    """Initialize MCP tools when configured."""
    logger.debug("Initializing MCP tools...")
    from doorae.graph.workflow import initialize_mcp_tools

    try:
        mcp_tools = await initialize_mcp_tools()
        if mcp_tools:
            total = sum(len(tools) for tools in mcp_tools.values())
            logger.info(f"MCP 도구 로드 완료: {total}개 도구 ({len(mcp_tools)}개 서버)")
            if not use_tui:
                console.print(
                    f"[green]✅ MCP 도구 로드 완료: {total}개 도구 ({len(mcp_tools)}개 서버)[/green]"
                )
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
    """Run the meeting in streaming mode."""
    setup_state = engine.setup_state or engine.setup()
    raw_start_time = setup_state.initial_state.get("start_time")
    start_time = float(raw_start_time) if isinstance(raw_start_time, (int, float)) else time.time()
    callback = CliMeetingCallback(start_time=start_time, hide_delegated=hide_delegated)
    await engine.run(callback)


def _require_server_address(server: str | None, *, command_name: str) -> str:
    examples = {
        "create": f"doorae create -s {DEFAULT_SERVER_EXAMPLE}",
        "join": f"doorae join <room_id> -s {DEFAULT_SERVER_EXAMPLE}",
        "rooms": f"doorae rooms -s {DEFAULT_SERVER_EXAMPLE}",
    }
    if server and server.strip():
        return server.strip()
    raise RuntimeError(
        "서버 주소를 지정하세요."
        f"\n  → 예: {examples.get(command_name, DEFAULT_SERVER_EXAMPLE)}"
    )


def _parse_host_port(server_address: str) -> tuple[str, int, str]:
    try:
        parsed = parse_server_address(server_address)
    except ServerAddressParseError as exc:
        message_by_reason = {
            "empty": f"서버 주소를 입력하세요.\n  → 예: {DEFAULT_SERVER_EXAMPLE}",
            "missing_host": f"서버 주소에 호스트가 없습니다.\n  → 예: {DEFAULT_SERVER_EXAMPLE}",
            "invalid_format": f"host:port 형식의 서버 주소만 사용할 수 있습니다.\n  → 예: {DEFAULT_SERVER_EXAMPLE}",
            "invalid_port": f"포트 번호가 올바르지 않습니다.\n  → 예: {DEFAULT_SERVER_EXAMPLE}",
            "missing_port": f"서버 주소에 포트가 없습니다.\n  → 예: {DEFAULT_SERVER_EXAMPLE}",
        }
        raise RuntimeError(message_by_reason[exc.reason]) from exc

    return parsed.host, parsed.port, parsed.netloc


def _render_cli_server_address(server_address: str) -> str:
    normalized = server_address.strip()
    if not normalized:
        return DEFAULT_SERVER_EXAMPLE
    if "://" not in normalized:
        return normalized

    parsed = urlsplit(normalized)
    base_path = parsed.path.rstrip("/")
    if base_path:
        http_scheme = "https" if parsed.scheme in {"https", "wss"} else "http"
        return urlunsplit((http_scheme, parsed.netloc, base_path, "", ""))
    return parsed.netloc or normalized


def _normalize_server_base_urls(server_address: str) -> tuple[str, str]:
    """Normalize a user-provided server address into WebSocket and HTTP base URLs."""
    normalized = server_address.strip()
    if not normalized:
        raise RuntimeError(f"서버 주소를 입력하세요.\n  → 예: {DEFAULT_SERVER_EXAMPLE}")

    if "://" not in normalized:
        _, _, netloc = _parse_host_port(normalized)
        return f"ws://{netloc}", f"http://{netloc}"

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"ws", "wss", "http", "https"}:
        raise RuntimeError(
            "지원하지 않는 서버 주소 형식입니다."
            f"\n  → 예: {DEFAULT_SERVER_EXAMPLE}"
        )
    if not parsed.netloc:
        raise RuntimeError(f"서버 주소에 호스트가 없습니다.\n  → 예: {DEFAULT_SERVER_EXAMPLE}")

    normalized_path = parsed.path.rstrip("/")
    ws_scheme = "wss" if parsed.scheme in {"https", "wss"} else "ws"
    http_scheme = "https" if parsed.scheme in {"https", "wss"} else "http"

    ws_base = urlunsplit((ws_scheme, parsed.netloc, normalized_path, "", ""))
    http_base = urlunsplit((http_scheme, parsed.netloc, normalized_path, "", ""))
    return ws_base, http_base


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail:
            return detail
    return response.text.strip() or f"HTTP {response.status_code}"


def _format_room_created_at(value: object) -> str:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "-"
        return text.replace("T", " ").replace("+00:00", "Z")

    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso(sep=" ", timespec="seconds").replace("+00:00", "Z")

    text = str(value).strip()
    return text or "-"


def _parse_room_list_payload(payload: object) -> list[RoomInfo]:
    if not isinstance(payload, list):
        raise RuntimeError("회의방 목록 응답 형식이 올바르지 않습니다.")

    validated_rooms: list[RoomInfo] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"회의방 목록 응답의 {index}번째 항목 형식이 올바르지 않습니다.")
        try:
            validated_rooms.append(RoomInfo.model_validate(item))
        except ValidationError as exc:
            raise RuntimeError(
                f"회의방 목록 응답의 {index}번째 항목 형식이 올바르지 않습니다: {exc.errors()[0]['loc']}"
            ) from exc
    return validated_rooms


def _print_rooms_table(rooms: list[RoomInfo]) -> None:
    if not rooms:
        console.print("등록된 회의방이 없습니다.")
        return

    table = Table(title="회의방 목록", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("이름", style="green")
    table.add_column("참여자 수", justify="right", style="yellow")
    table.add_column("생성 시간", style="magenta")

    for room in rooms:
        table.add_row(
            room.id,
            room.name,
            str(room.participants_count),
            _format_room_created_at(room.created_at),
        )

    console.print(table)


async def _list_server_rooms(server_address: str) -> None:
    _, http_base = _normalize_server_base_urls(server_address)

    try:
        async with httpx.AsyncClient(base_url=http_base, timeout=10.0) as client:
            response = await client.get("/api/rooms")
            if response.is_error:
                raise RuntimeError(
                    f"회의방 목록 조회에 실패했습니다: {_extract_error_detail(response)}"
                )
            payload = response.json()
    except httpx.ConnectError:
        raise RuntimeError(
            f"서버에 연결할 수 없습니다: {http_base}"
            f"\n  → 서버가 실행 중인지 확인하세요: uv run doorae serve -s {_render_cli_server_address(server_address)}"
        )
    except RuntimeError:
        raise
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"서버 통신 중 오류가 발생했습니다: {exc}"
            f"\n  → 서버가 실행 중인지 확인하세요: uv run doorae serve -s {_render_cli_server_address(server_address)}"
        ) from exc

    _print_rooms_table(_parse_room_list_payload(payload))


async def _setup_server_room(
    server_address: str,
    room_id: str | None,
    username: str,
) -> ServerSessionConfig:
    """Create or validate the target room and build the concrete URLs for TUI mode."""
    ws_base, http_base = _normalize_server_base_urls(server_address)
    cli_server_address = _render_cli_server_address(server_address)

    try:
        async with httpx.AsyncClient(base_url=http_base, timeout=10.0) as client:
            if room_id is None:
                create_response = await client.post(
                    "/api/rooms",
                    json={"name": f"Doorae Room ({username})"},
                )
                if create_response.is_error:
                    raise RuntimeError(
                        f"회의방 생성에 실패했습니다: {_extract_error_detail(create_response)}"
                    )
                payload = create_response.json()
                room_id = str(payload["id"])
            else:
                room_response = await client.get(f"/api/rooms/{quote(room_id, safe='')}")
                if room_response.status_code == 404:
                    raise RuntimeError(
                        f"회의방을 찾을 수 없습니다: {room_id}"
                        f"\n  → 'doorae rooms -s {cli_server_address}'로 목록을 확인하세요"
                    )
                if room_response.is_error:
                    raise RuntimeError(
                        f"회의방 조회에 실패했습니다: {_extract_error_detail(room_response)}"
                    )
    except httpx.ConnectError:
        raise RuntimeError(
            f"서버에 연결할 수 없습니다: {http_base}"
            f"\n  → 서버가 실행 중인지 확인하세요: uv run doorae serve -s {cli_server_address}"
        )
    except RuntimeError:
        raise
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"서버 통신 중 오류가 발생했습니다: {exc}"
            f"\n  → 서버가 실행 중인지 확인하세요: uv run doorae serve -s {cli_server_address}"
        ) from exc

    quoted_room_id = quote(room_id, safe="")
    quoted_username = quote(username, safe="")
    normalized_ws_base = ws_base.rstrip("/")
    normalized_http_base = http_base.rstrip("/")
    return ServerSessionConfig(
        room_id=room_id,
        ws_url=f"{normalized_ws_base}/ws/{quoted_room_id}?username={quoted_username}",
        start_url=f"{normalized_http_base}/api/rooms/{quoted_room_id}/start",
    )


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[Path] = None,
    settings: Optional[Settings] = None,
    use_tui: bool = False,
    hide_delegated: bool = False,
) -> None:
    """Run a meeting using the shared Doorae runtime."""
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
                title="🚀 Doorae",
                border_style="green",
            )
        )

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    stderr_backup = None
    stderr_file = None
    if use_tui:
        stderr_backup = sys.stderr
        stderr_file = open("doorae.log", "a", encoding="utf-8")
        sys.stderr = stderr_file

    try:
        if use_tui:
            await _run_local_tui_meeting(
                settings=settings,
                profiles_path=profiles_path,
                initial_message=initial_message,
            )
            return

        mcp_tools = await _initialize_mcp(settings, use_tui=False)

        from doorae.interfaces.engine import MeetingEngine

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
        logger.debug("Running workflow (stream=True)...")

        await _run_streaming(engine, hide_delegated=hide_delegated)

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


async def _run_local_tui_meeting(
    *,
    settings: Settings,
    profiles_path: Path,
    initial_message: str,
) -> None:
    from doorae.interfaces.tui import MeetingTuiApp

    mcp_tools = await _initialize_mcp(settings, use_tui=True)
    tui_app = MeetingTuiApp(
        settings=settings,
        profiles_path=str(profiles_path),
        initial_message=initial_message,
        mcp_tools=mcp_tools,
        server_url=None,
        server_start_url=None,
        server_username="user",
        room_id=None,
        show_server_invite=False,
    )
    await tui_app.run_async()


async def run_server_meeting(
    *,
    initial_message: str,
    profiles_path: Optional[Path] = None,
    settings: Optional[Settings] = None,
    server_address: str,
    room_id: str | None,
    username: str,
) -> None:
    """Connect to a remote Doorae room and run the TUI client."""
    if settings is None:
        settings = get_settings()

    if profiles_path is None:
        profiles_path = Path(settings.agent_profiles_path)

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    stderr_backup = sys.stderr
    stderr_file = open("doorae.log", "a", encoding="utf-8")
    sys.stderr = stderr_file

    try:
        from doorae.interfaces.tui import MeetingTuiApp

        server_session = await _setup_server_room(server_address, room_id, username)
        tui_app = MeetingTuiApp(
            settings=settings,
            profiles_path=str(profiles_path),
            initial_message=initial_message,
            mcp_tools=None,
            server_url=server_session.ws_url,
            server_start_url=server_session.start_url,
            server_username=username,
            room_id=server_session.room_id,
            show_server_invite=room_id is None,
        )
        await tui_app.run_async()
    finally:
        sys.stderr = stderr_backup
        stderr_file.close()


if __name__ == "__main__":
    app()
