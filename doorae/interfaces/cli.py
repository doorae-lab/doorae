#!/usr/bin/env python3
"""Doorae CLI - AI-powered team meeting system."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from urllib.parse import quote, urlsplit, urlunsplit

import httpx
import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from doorae import __version__
from doorae.config import Settings, get_settings, setup_tracing
from doorae.interfaces.event_utils import random_speaker_color
from doorae.interfaces.logging import setup_logging
from doorae.interfaces.time_utils import format_elapsed
from doorae.project import WorkspaceError, init_workspace

if TYPE_CHECKING:
    from doorae.interfaces.engine import MeetingEngine


app = typer.Typer(
    name="doorae",
    help="Doorae - AI-powered team meeting system",
    add_completion=False,
)
console = Console()
DEFAULT_MESSAGE = "회의를 시작합니다"


@dataclass(slots=True)
class ServerSessionConfig:
    room_id: str
    ws_url: str
    start_url: str


def _status_emoji(status: str) -> str:
    """Load agenda status icons lazily to keep help/version import-light."""
    from doorae.graph.constants import STATUS_EMOJI

    return STATUS_EMOJI.get(status, "?")


def should_use_tui(no_tui_flag: bool) -> bool:
    """Return whether the interactive TUI should be used."""
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
    no_stream: bool,
    no_tui: bool,
    server: str | None,
    room: str | None,
    username: str,
    config: Optional[Path],
    verbose: bool,
    quiet: bool,
    version: bool,
    trace: Optional[bool],
    hide_delegated: bool,
) -> None:
    if version:
        console.print(f"Doorae version: {__version__}")
        raise typer.Exit(code=0)

    if server and no_tui:
        logger.warning(
            "--no-tui 옵션은 무시됩니다: 서버 모드는 TUI를 통해 WebSocket 이벤트를 표시합니다"
        )
    use_tui = True if server else should_use_tui(no_tui)
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

    try:
        asyncio.run(
            run_meeting(
                initial_message=message,
                profiles_path=profiles,
                stream=stream,
                settings=settings,
                use_tui=use_tui,
                server_url=server,
                room_id=room,
                username=username,
                hide_delegated=hide_delegated,
            )
        )
    except RuntimeError as exc:
        if server is not None:
            console.print(f"[bold red]오류:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        raise


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
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        help="스트리밍 모드 비활성화 (배치 모드 사용)",
    ),
    no_tui: bool = typer.Option(
        False,
        "--no-tui",
        help="TUI 모드 비활성화 (클래식 CLI 출력 사용)",
    ),
    server: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        help="서버 모드 URL (예: http://localhost:8000). 먼저 서버를 실행하세요: uv run doorae-server",
    ),
    room: Optional[str] = typer.Option(
        None,
        "--room",
        "-r",
        help="연결할 회의방 ID (생략 시 새 회의방 자동 생성)",
    ),
    username: str = typer.Option(
        "user",
        "--username",
        "-u",
        help="서버 모드에서 표시될 사용자 이름",
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
    if ctx.invoked_subcommand is not None:
        return

    _run_default_command(
        message=message,
        profiles=profiles,
        no_stream=no_stream,
        no_tui=no_tui,
        server=server,
        room=room,
        username=username,
        config=config,
        verbose=verbose,
        quiet=quiet,
        version=version,
        trace=trace,
        hide_delegated=hide_delegated,
    )


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


async def _run_batch(workflow, state: dict, config: dict) -> dict:
    """Run the meeting in batch mode."""
    logger.debug("Invoking workflow...")
    result = await workflow.ainvoke(state, config=config)
    logger.debug(f"Workflow completed. Result keys: {result.keys()}")

    console.print("\n[bold]📝 회의 기록[/bold]")
    console.rule(style="yellow")

    speaker_colors: dict[str, str] = {}

    for message in result.get("messages", []):
        speaker = getattr(message, "name", "System")
        if speaker not in speaker_colors:
            speaker_colors[speaker] = random_speaker_color()
        color = speaker_colors[speaker]

        console.print(f"\n[bold {color}][{speaker}][/bold {color}]")
        console.print(message.content)
        console.rule(style="dim")

    _print_summary_table(result.get("agendas"), result.get("speaker_counts"))
    return result


def _normalize_server_base_urls(server_url: str) -> tuple[str, str]:
    """Normalize a user-provided server URL into WebSocket and HTTP base URLs."""
    parsed = urlsplit(server_url)
    if parsed.scheme not in {"ws", "wss", "http", "https"}:
        raise RuntimeError(
            "지원하지 않는 서버 URL 스킴입니다."
            "\n  → 예: http://localhost:8000"
        )
    if not parsed.netloc:
        raise RuntimeError("서버 URL에 호스트가 없습니다.")

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


async def _setup_server_room(
    server_url: str,
    room_id: str | None,
    username: str,
) -> ServerSessionConfig:
    """Create or validate the target room and build the concrete URLs for TUI mode."""
    ws_base, http_base = _normalize_server_base_urls(server_url)

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
                        "\n  → --room을 생략하면 새 회의방이 자동 생성됩니다"
                    )
                if room_response.is_error:
                    raise RuntimeError(
                        f"회의방 조회에 실패했습니다: {_extract_error_detail(room_response)}"
                    )
    except httpx.ConnectError:
        raise RuntimeError(
            f"서버에 연결할 수 없습니다: {http_base}"
            "\n  → 서버가 실행 중인지 확인하세요: uv run doorae-server"
        )
    except RuntimeError:
        raise
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"서버 통신 중 오류가 발생했습니다: {exc}"
            "\n  → 서버가 실행 중인지 확인하세요: uv run doorae-server"
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
    stream: bool = False,
    settings: Optional[Settings] = None,
    use_tui: bool = False,
    server_url: str | None = None,
    room_id: str | None = None,
    username: str = "user",
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
            from doorae.interfaces.tui import MeetingTuiApp

            server_session: ServerSessionConfig | None = None
            if server_url is not None:
                server_session = await _setup_server_room(server_url, room_id, username)

            mcp_tools = None
            if server_session is None:
                mcp_tools = await _initialize_mcp(settings, use_tui=True)

            tui_app = MeetingTuiApp(
                settings=settings,
                profiles_path=str(profiles_path),
                initial_message=initial_message,
                mcp_tools=mcp_tools,
                server_url=server_session.ws_url if server_session else None,
                server_start_url=server_session.start_url if server_session else None,
                server_username=username,
                room_id=server_session.room_id if server_session else None,
                show_server_invite=server_session is not None and room_id is None,
            )
            await tui_app.run_async()
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
    app()
