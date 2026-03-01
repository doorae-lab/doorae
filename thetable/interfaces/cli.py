#!/usr/bin/env python3
"""TheTable CLI - AI-powered team meeting system"""
import os
import sys
import asyncio
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
from thetable.graph.workflow import build_initial_state, create_meeting_workflow
from thetable.graph.constants import STATUS_EMOJI, HOST_ROLE_NAME, AGENT_COLORS
from thetable.interfaces.logging import setup_logging


app = typer.Typer(
    name="thetable",
    help="TheTable - AI-powered team meeting system",
    add_completion=False,
)
console = Console()


def should_use_tui(no_tui_flag: bool) -> bool:
    """TUI 모드 사용 여부를 결정한다.

    Returns True only when: TTY detected AND terminal >= 80×24 AND --no-tui not set.
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


# 스트리밍 이벤트 핸들러
def _handle_chain_start(event: dict, state_ref: dict) -> None:
    """on_chain_start 이벤트 처리 - 안건 상태 표시"""
    name = event.get("name", "")
    if name != "process_response":
        return

    data = event.get("data", {})
    input_data = data.get("input", {})
    current_idx = input_data.get("current_agenda_idx", 0)
    agendas = input_data.get("agendas", [])

    # 상태 변경 감지
    current_state = (
        current_idx,
        tuple((a["title"], a["status"]) for a in agendas)
    )

    if current_state != state_ref.get("prev_agenda_state"):
        state_ref["prev_agenda_state"] = current_state
        # 안건 패널 출력
        panel = format_agenda_panel(agendas, current_idx, state_ref["start_time"])
        console.print(panel)
        console.print()


def _handle_chat_model_start(event: dict, state_ref: dict) -> None:
    """on_chat_model_start 이벤트 처리 - 발언자 표시"""
    speaker = event.get("name")

    # run_name이 없으면 tags에서 speaker: 접두사 찾기
    if not speaker or speaker == "ChatOpenAI":
        tags = event.get("tags", [])
        for tag in tags:
            if tag.startswith("speaker:"):
                speaker = tag.replace("speaker:", "")
                break

    # 발언자가 변경되었으면 표시
    if speaker and speaker not in ("ChatOpenAI", "RunnableSequence") and speaker != state_ref.get("current_speaker"):
        if state_ref.get("current_speaker"):
            console.print()  # 이전 발언 줄바꿈
        console.print(f"\n[bold cyan][{speaker}][/bold cyan]")
        state_ref["current_speaker"] = speaker


def _handle_chat_model_stream(event: dict) -> None:
    """on_chat_model_stream 이벤트 처리 - 토큰 출력"""
    tags = event.get("tags", [])
    if "participant" not in tags:
        return

    chunk = event["data"]["chunk"]
    content = getattr(chunk, "content", "")
    if content:
        console.print(content, end="")


def _handle_chat_model_end(event: dict) -> None:
    """on_chat_model_end 이벤트 처리 - 응답 완료"""
    tags = event.get("tags", [])
    if "participant" in tags:
        console.print()  # 줄바꿈
        console.rule(style="dim")


def _handle_chain_end(event: dict, state_ref: dict) -> None:
    """on_chain_end 이벤트 처리 - pending_speakers 표시 및 상태 누적"""
    tags = event.get("tags", [])
    if "langgraph_node" not in tags:
        return

    # node_name 추출
    try:
        idx = tags.index("langgraph_node")
        node_name = tags[idx + 1] if idx + 1 < len(tags) else None
    except (ValueError, IndexError):
        return

    if node_name != "process_response":
        return

    data = event.get("data", {})
    output_data = data.get("output", {})
    pending = output_data.get("pending_speakers", [])

    if pending:
        console.print(f"[dim]다음 발언 예정: {', '.join(pending)}[/dim]")

    # 상태 누적 (요약 테이블용)
    if "agendas" in output_data:
        state_ref["agendas"] = output_data["agendas"]
    if "speaker_counts" in output_data:
        state_ref["speaker_counts"] = output_data["speaker_counts"]


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

    # 안건 상태
    if agendas:
        completed = sum(1 for a in agendas if a["status"] == "completed")
        table.add_row("완료된 안건", f"{completed}/{len(agendas)}")

    # 발언 횟수
    if speaker_counts:
        for speaker, count in speaker_counts.items():
            table.add_row(f"{speaker} 발언 횟수", str(count))

    console.print("\n")
    console.print(table)


def format_agenda_panel(
    agendas: List[dict],
    current_idx: int,
    start_time: float
) -> Panel:
    """안건 상태를 Rich Panel로 포맷팅

    Args:
        agendas: 안건 리스트
        current_idx: 현재 안건 인덱스
        start_time: 회의 시작 시간 (Unix timestamp)

    Returns:
        Rich Panel 객체
    """
    lines = []

    for i, agenda in enumerate(agendas):
        # 상태 이모지
        status_emoji = STATUS_EMOJI.get(agenda["status"], "❓")

        # owner: required_speakers의 첫 번째
        owner = agenda.get("required_speakers", [""])[0] if agenda.get("required_speakers") else ""

        # 시간 계산
        time_str = ""
        if agenda["status"] == "in_progress":
            # 진행 중: 경과 시간
            agenda_start = agenda.get("start_time") or start_time
            elapsed = time.time() - agenda_start
            mins, secs = divmod(int(elapsed), 60)
            time_str = f" [{mins}m {secs}s]"
        elif agenda["status"] == "completed":
            # 완료: 총 소요 시간
            agenda_start = agenda.get("start_time")
            agenda_end = agenda.get("end_time")
            if agenda_start and agenda_end:
                elapsed = agenda_end - agenda_start
                mins, secs = divmod(int(elapsed), 60)
                time_str = f" [{mins}m {secs}s]"

        # 현재 안건 표시
        indicator = " ← 현재" if i == current_idx else ""

        # 라인 구성
        title = agenda["title"]
        line = f"  {status_emoji} {i+1}. {title} ({owner}){time_str}{indicator}"
        lines.append(line)

        # 결정사항 표시 (있으면)
        if agenda.get("decision"):
            lines.append(f"     └─ {agenda['decision']}")

    return Panel(
        "\n".join(lines),
        title="📋 안건 진행 상태",
        border_style="magenta"
    )


@app.command()
def main(
    message: str = typer.Option(
        "회의를 시작합니다",
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
) -> None:
    """TheTable CLI - AI 기반 팀 회의 시스템

    Examples:

        # 기본 메시지로 회의 시작

        thetable

        # 커스텀 메시지로 회의 시작

        thetable --message "오늘 스프린트 회의를 시작합니다"
        thetable -m "긴급 회의"

        # 다른 옵션과 함께 사용

        thetable --message "회의 시작" -v
        thetable --profiles config/custom.yaml

        # 배치 모드 사용 (스트리밍 비활성화)

        thetable --no-stream
    """
    # 버전 출력
    if version:
        console.print(f"TheTable version: {__version__}")
        raise typer.Exit(code=0)

    # 로깅 설정
    use_tui = should_use_tui(no_tui)
    setup_logging(verbose=verbose, quiet=quiet, use_tui=use_tui)

    # 스트리밍 모드 계산 (--no-stream 플래그의 반대)
    stream = not no_stream

    # 설정 로드
    settings = get_settings(config_path=config)

    # CLI 플래그가 None이면 환경변수 값 사용
    tracing_enabled = trace if trace is not None else settings.langchain_tracing_v2
    setup_tracing(
        enabled=tracing_enabled,
        api_key=settings.langchain_api_key,
        project=settings.langchain_project,
        endpoint=settings.langchain_endpoint,
    )

    # 비동기 실행
    asyncio.run(run_meeting(
        initial_message=message,
        profiles_path=profiles,
        stream=stream,
        settings=settings,
        use_tui=use_tui,
    ))


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
            total = sum(len(t) for t in mcp_tools.values())
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
    except Exception as e:
        logger.warning(f"MCP 초기화 실패: {e}")
        if not use_tui:
            console.print(f"[yellow]⚠️  MCP 초기화 실패: {e}[/yellow]")
            console.print("[yellow]   확인 사항:[/yellow]")
            console.print("[yellow]   1. config/mcp_servers.json 파일 존재 여부[/yellow]")
            console.print("[yellow]   2. .env 파일의 GITHUB_PERSONAL_ACCESS_TOKEN 설정 여부[/yellow]")
        return None


def _build_initial_state(
    settings: Settings,
    initial_message: str,
    human_names: list[str],
    agendas: list[dict]
) -> dict:
    """초기 상태 구성을 graph 모듈 함수에 위임."""
    return build_initial_state(settings, initial_message, human_names, agendas)


async def _run_streaming(workflow, state: dict, config: dict) -> None:
    """스트리밍 모드 실행

    Args:
        workflow: 워크플로우 인스턴스
        state: 초기 상태
        config: LangGraph 설정
    """
    state_ref = {
        "current_speaker": None,
        "prev_agenda_state": None,
        "start_time": state["start_time"],
        "agendas": None,
        "speaker_counts": None,
    }

    # 이벤트 핸들러 매핑
    event_handlers = {
        "on_chain_start": _handle_chain_start,
        "on_chat_model_start": _handle_chat_model_start,
        "on_chat_model_stream": _handle_chat_model_stream,
        "on_chat_model_end": _handle_chat_model_end,
        "on_chain_end": _handle_chain_end,
    }

    async for event in workflow.astream_events(state, config=config, version="v2"):
        kind = event["event"]
        handler = event_handlers.get(kind)
        if handler:
            # state_ref를 받는 핸들러와 받지 않는 핸들러 구분
            if kind in ("on_chain_start", "on_chat_model_start", "on_chain_end"):
                handler(event, state_ref)
            else:
                handler(event)

    # 스트리밍 완료 후 요약 테이블 출력
    _print_summary_table(state_ref.get("agendas"), state_ref.get("speaker_counts"))


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

    # 결과 출력
    console.print("\n[bold]📝 회의 기록[/bold]")
    console.rule(style="yellow")

    # 참가자 목록 추출 및 색상 할당
    speakers = list(dict.fromkeys(getattr(msg, "name", "System") for msg in result.get("messages", [])))
    color_map = {speaker: AGENT_COLORS[i % len(AGENT_COLORS)] for i, speaker in enumerate(speakers)}

    for msg in result.get("messages", []):
        speaker = getattr(msg, "name", "System")
        color = color_map.get(speaker, "white")

        console.print(f"\n[bold {color}][{speaker}][/bold {color}]")
        console.print(msg.content)
        console.rule(style="dim")

    # 메타 정보 테이블
    _print_summary_table(result.get("agendas"), result.get("speaker_counts"))

    return result


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[Path] = None,
    stream: bool = False,
    settings: Optional[Settings] = None,
    use_tui: bool = False,
) -> None:
    """회의 실행.

    Args:
        initial_message: 회의 시작 메시지
        profiles_path: agent_profiles.yaml 경로 (None이면 설정값 사용)
        stream: 스트리밍 모드 사용 여부
        settings: Settings 인스턴스 (None이면 기본 설정 사용)
        use_tui: TUI 모드 여부 (True면 stderr를 로그 파일로 리다이렉트)
    """
    # 설정이 없으면 기본 설정 로드
    if settings is None:
        settings = get_settings()

    # 프로필 경로 결정
    if profiles_path is None:
        profiles_path = Path(settings.agent_profiles_path)

    # 회의 시작 패널
    if not use_tui:
        console.print(
            Panel(
                f"[bold]회의 시작[/bold]\n\n"
                f"프로필: [cyan]{profiles_path}[/cyan]\n"
                f"Main LLM: [yellow]{settings.llm_main_model}[/yellow] "
                f"(온도: {settings.llm_main_temperature})\n"
                f"Task LLM: [yellow]{settings.llm_task_model}[/yellow] "
                f"(온도: {settings.llm_task_temperature})",
                title="🚀 TheTable",
                border_style="green",
            )
        )

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    # TUI 모드: stderr를 로그 파일로 리다이렉트 (MCP subprocess stderr 격리)
    stderr_backup = None
    stderr_file = None
    if use_tui:
        stderr_backup = sys.stderr
        stderr_file = open("thetable.log", "a")
        sys.stderr = stderr_file

    try:
        # MCP Tools 초기화
        mcp_tools = await _initialize_mcp(settings, use_tui=use_tui)

        # Workflow 생성
        logger.debug("Creating workflow...")
        workflow = create_meeting_workflow(
            profiles_path=str(profiles_path),
            mcp_tools=mcp_tools or {}
        )
        logger.debug(f"Workflow created: {workflow}")

        # Human 프로필 이름 추출
        from thetable.core.profile import load_agent_profiles
        profiles = load_agent_profiles(str(profiles_path))
        human_names = [name for name, p in profiles.items() if p.is_human]
        logger.debug(f"Human participants: {human_names}")

        # 안건 로드
        from thetable.core.agenda import load_agendas
        agendas = load_agendas(str(settings.agendas_path))

        # 초기 상태 구성
        initial_state = _build_initial_state(settings, initial_message, human_names, agendas)
        logger.debug(f"Initial state: {initial_state}")

        # 실행
        logger.debug(f"Running workflow (stream={stream})...")
        graph_config = {"recursion_limit": settings.recursion_limit}

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

        if stream:
            await _run_streaming(workflow, initial_state, graph_config)
        else:
            await _run_batch(workflow, initial_state, graph_config)

        # 회의 종료 패널
        console.print(
            Panel(
                "[bold green]회의 종료[/bold green]",
                border_style="green",
            )
        )
    finally:
        # TUI 모드: stderr 복원
        if stderr_backup is not None:
            sys.stderr = stderr_backup
        if stderr_file is not None:
            stderr_file.close()


if __name__ == "__main__":
    app()
