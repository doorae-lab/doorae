#!/usr/bin/env python3
"""TheTable CLI - AI-powered team meeting system"""
import asyncio
import time
from pathlib import Path
from typing import List, Optional

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langchain_core.messages import HumanMessage

from thetable import __version__
from thetable.config import Settings, get_settings, setup_tracing
from thetable.graph.workflow import create_meeting_workflow
from thetable.interfaces.logging import setup_logging


app = typer.Typer(
    name="thetable",
    help="TheTable - AI-powered team meeting system",
    add_completion=False,
)
console = Console()


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
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "deferred": "⏸️"
        }.get(agenda["status"], "❓")

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

        thetable --message "회의 시작" --stream -v
        thetable --profiles config/custom.yaml
    """
    # 버전 출력
    if version:
        console.print(f"TheTable version: {__version__}")
        raise typer.Exit(code=0)

    # 로깅 설정
    setup_logging(verbose=verbose, quiet=quiet)

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
    ))


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[Path] = None,
    stream: bool = False,
    settings: Optional[Settings] = None,
) -> None:
    """회의 실행.

    Args:
        initial_message: 회의 시작 메시지
        profiles_path: agent_profiles.yaml 경로 (None이면 설정값 사용)
        stream: 스트리밍 모드 사용 여부
        settings: Settings 인스턴스 (None이면 기본 설정 사용)
    """
    # 설정이 없으면 기본 설정 로드
    if settings is None:
        settings = get_settings()

    # 프로필 경로 결정
    if profiles_path is None:
        profiles_path = Path(settings.agent_profiles_path)

    # 회의 시작 패널
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

    # MCP Tools 초기화
    logger.debug("Initializing MCP tools...")
    from thetable.graph.workflow import initialize_mcp_tools
    try:
        mcp_tools = await initialize_mcp_tools()
        if mcp_tools:
            total = sum(len(t) for t in mcp_tools.values())
            console.print(f"[green]✅ MCP 도구 로드 완료: {total}개 도구 ({len(mcp_tools)}개 서버)[/green]")
        else:
            console.print("[yellow]⚠️  MCP 도구를 사용할 수 없습니다 (설정 또는 환경변수 확인 필요)[/yellow]")
    except Exception as e:
        logger.warning(f"MCP 초기화 실패: {e}")
        console.print(f"[yellow]⚠️  MCP 초기화 실패: {e}[/yellow]")
        mcp_tools = None

    # Workflow 생성
    logger.debug("Creating workflow...")
    workflow = create_meeting_workflow(
        profiles_path=str(profiles_path),
        mcp_tools=mcp_tools
    )
    logger.debug(f"Workflow created: {workflow}")

    # Human 프로필 이름 추출
    from thetable.core.profile import load_agent_profiles
    profiles = load_agent_profiles(str(profiles_path))
    human_names = [name for name, p in profiles.items() if p.is_human]
    logger.debug(f"Human participants: {human_names}")

    # 초기 상태 - 안건 기반
    import time
    
    # 기본 안건 정의
    base_agendas = [
        {
            "title": "회의 시작 및 현황 공유",
            "description": "회의를 시작하고 주간 현황을 공유합니다",
            "status": "in_progress",
            "required_speakers": ["Host", "PM"],
            "start_time": time.time()
        },
        {
            "title": "주요 이슈 논의",
            "description": "당면한 문제들을 논의하고 해결 방안을 모색합니다",
            "status": "pending",
            "required_speakers": ["TechLead", "Designer", "DevOps"]
        },
        {
            "title": "향후 일정 및 계획",
            "description": "다음 단계 일정과 계획을 수립합니다",
            "status": "pending",
            "required_speakers": ["PM", "TechLead"]
        },
        {
            "title": "회의 마무리",
            "description": "논의 내용을 정리하고 액션 아이템을 확정합니다",
            "status": "pending",
            "required_speakers": ["Host"]
        },
    ]
    
    # Human 참여자를 모든 안건에 추가
    for agenda in base_agendas:
        for human_name in human_names:
            if human_name not in agenda["required_speakers"]:
                agenda["required_speakers"].append(human_name)
    
    initial_state = {
        "messages": [HumanMessage(content=initial_message)],
        "agendas": base_agendas,
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": time.time(),
        "max_turns": settings.max_turns,
    }
    logger.debug(f"Initial state: {initial_state}")

    # 실행
    logger.debug(f"Running workflow (stream={stream})...")
    
    # LangGraph config 설정
    graph_config = {"recursion_limit": settings.recursion_limit}
    
    if stream:
        # 스트리밍 모드 - astream_events()로 토큰 단위 출력
        current_speaker = None
        prev_agenda_state = None

        async for event in workflow.astream_events(initial_state, config=graph_config, version="v2"):
            kind = event["event"]
            
            # on_chain_start: 노드 시작 시 안건 정보 표시
            if kind == "on_chain_start":
                name = event.get("name", "")

                # 안건 상태 변경 감지 및 패널 출력 (process_response 노드에서)
                if name == "process_response":
                    data = event.get("data", {})
                    input_data = data.get("input", {})
                    current_idx = input_data.get("current_agenda_idx", 0)
                    agendas = input_data.get("agendas", [])

                    # 상태 변경 감지
                    current_state = (
                        current_idx,
                        tuple((a["title"], a["status"]) for a in agendas)
                    )

                    if current_state != prev_agenda_state:
                        prev_agenda_state = current_state

                        # 안건 패널 출력
                        panel = format_agenda_panel(agendas, current_idx, initial_state["start_time"])
                        console.print(panel)
                        console.print()  # 빈 줄
            
            # on_chat_model_start: LLM 호출 시작 (발언자 이름 출력)
            elif kind == "on_chat_model_start":
                # run_name에서 발언자 추출
                speaker = event.get("name")
                
                # run_name이 없으면 tags에서 speaker: 접두사 찾기
                if not speaker or speaker == "ChatOpenAI":
                    tags = event.get("tags", [])
                    for tag in tags:
                        if tag.startswith("speaker:"):
                            speaker = tag.replace("speaker:", "")
                            break
                
                # 발언자가 변경되었으면 표시
                if speaker and speaker not in ("ChatOpenAI", "RunnableSequence") and speaker != current_speaker:
                    if current_speaker:
                        console.print()  # 이전 발언 줄바꿈
                    console.print(f"\n[bold cyan][{speaker}][/bold cyan]")
                    current_speaker = speaker
            
            # on_chat_model_stream: 토큰 단위 출력 (참여자 응답만)
            elif kind == "on_chat_model_stream":
                tags = event.get("tags", [])
                if "participant" in tags:
                    chunk = event["data"]["chunk"]
                    content = getattr(chunk, "content", "")
                    if content:
                        console.print(content, end="")
            
            # on_chat_model_end: LLM 응답 완료 (줄바꿈 및 구분선, 참여자 응답만)
            elif kind == "on_chat_model_end":
                tags = event.get("tags", [])
                if "participant" in tags:
                    console.print()  # 줄바꿈
                    console.rule(style="dim")
            
            # on_chain_end: 노드 종료 시 pending_speakers 표시
            elif kind == "on_chain_end":
                metadata = event.get("metadata", {})
                tags = event.get("tags", [])
                
                # process_response 노드 종료 시 pending_speakers 표시
                if "langgraph_node" in tags:
                    node_name = tags[tags.index("langgraph_node") + 1] if tags.index("langgraph_node") + 1 < len(tags) else None
                    
                    if node_name == "process_response":
                        data = event.get("data", {})
                        output_data = data.get("output", {})
                        pending = output_data.get("pending_speakers", [])
                        
                        if pending:
                            console.print(f"[dim]다음 발언 예정: {', '.join(pending)}[/dim]")
    else:
        # 일반 모드
        logger.debug("Invoking workflow...")
        result = await workflow.ainvoke(initial_state, config=graph_config)
        logger.debug(f"Workflow completed. Result keys: {result.keys()}")

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
        if "agendas" in result or "speaker_counts" in result:
            table = Table(title="회의 요약", show_header=True)
            table.add_column("항목", style="cyan")
            table.add_column("값", style="yellow")

            # 안건 상태
            if "agendas" in result:
                agendas = result["agendas"]
                completed = sum(1 for a in agendas if a["status"] == "completed")
                table.add_row("완료된 안건", f"{completed}/{len(agendas)}")

            # 발언 횟수
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
