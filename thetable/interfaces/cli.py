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
from thetable.config import Settings, get_settings, setup_tracing
from thetable.graph.workflow import create_meeting_workflow
from thetable.interfaces.logging import setup_logging


app = typer.Typer(
    name="thetable",
    help="TheTable - AI-powered team meeting system",
    add_completion=False,
)
console = Console()


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
            f"모델: [yellow]{settings.llm_model}[/yellow] "
            f"(온도: {settings.llm_temperature})",
            title="🚀 TheTable",
            border_style="green",
        )
    )

    logger.debug(f"Settings loaded: {settings}")
    logger.debug(f"Profiles path: {profiles_path}")

    # Workflow 생성
    logger.debug("Creating workflow...")
    workflow = create_meeting_workflow(profiles_path=str(profiles_path))
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
            "status": "pending",
            "required_speakers": ["Host", "PM"]
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
    }
    logger.debug(f"Initial state: {initial_state}")

    # 실행
    logger.debug(f"Running workflow (stream={stream})...")
    if stream:
        # 스트리밍 모드 - astream_events()로 토큰 단위 출력
        current_speaker = None
        current_agenda_title = None
        
        async for event in workflow.astream_events(initial_state, version="v2"):
            kind = event["event"]
            
            # on_chain_start: 노드 시작 시 안건 정보 표시
            if kind == "on_chain_start":
                metadata = event.get("metadata", {})
                tags = event.get("tags", [])
                
                # StateGraph 노드 시작 감지
                if "langgraph_node" in tags:
                    node_name = tags[tags.index("langgraph_node") + 1] if tags.index("langgraph_node") + 1 < len(tags) else None
                    
                    # 안건 정보 표시 (process_response 노드에서)
                    if node_name == "process_response":
                        data = event.get("data", {})
                        input_data = data.get("input", {})
                        current_idx = input_data.get("current_agenda_idx", 0)
                        agendas = input_data.get("agendas", [])
                        
                        if current_idx < len(agendas):
                            agenda_title = agendas[current_idx]["title"]
                            if agenda_title != current_agenda_title:
                                current_agenda_title = agenda_title
                                console.print(f"\n[bold magenta]📋 안건 {current_idx + 1}: {agenda_title}[/bold magenta]")
                                console.rule(style="magenta")
            
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
            
            # on_chat_model_stream: 토큰 단위 출력
            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = getattr(chunk, "content", "")
                if content:
                    console.print(content, end="")
            
            # on_chat_model_end: LLM 응답 완료 (줄바꿈 및 구분선)
            elif kind == "on_chat_model_end":
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
        result = await workflow.ainvoke(initial_state)
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
