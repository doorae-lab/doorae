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


@app.command()
def main(
    message: Optional[str] = typer.Argument(
        None,
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
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="버전 정보 출력",
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
    # 버전 출력
    if version:
        console.print(f"TheTable version: {__version__}")
        raise typer.Exit(code=0)

    # message가 없으면 에러
    if message is None:
        console.print("[red]Error: message argument is required[/red]")
        raise typer.Exit(code=1)

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
