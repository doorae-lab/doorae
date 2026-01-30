#!/usr/bin/env python3
"""TheTable CLI - AI-powered team meeting system"""
import argparse
import asyncio
from typing import Optional
from langchain_core.messages import HumanMessage

from thetable.config import get_settings
from thetable.graph.workflow import create_meeting_workflow


async def run_meeting(
    initial_message: str,
    profiles_path: Optional[str] = None,
    stream: bool = False,
) -> None:
    """회의 실행.

    Args:
        initial_message: 회의 시작 메시지
        profiles_path: agent_profiles.yaml 경로 (None이면 설정값 사용)
        stream: 스트리밍 모드 사용 여부
    """
    settings = get_settings()

    # 프로필 경로 결정
    if profiles_path is None:
        profiles_path = settings.agent_profiles_path

    # Workflow 생성
    print(f"🚀 회의 시작 (프로필: {profiles_path})")
    print(f"📋 모델: {settings.llm_model} (온도: {settings.llm_temperature})")
    print("-" * 60)

    workflow = create_meeting_workflow(profiles_path=profiles_path)

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
                    print(f"\n[{speaker}]")
                    print(msg.content)
                    print("-" * 60)
    else:
        # 일반 모드
        result = await workflow.ainvoke(initial_state)

        # 결과 출력
        print("\n📝 회의 기록:")
        print("=" * 60)
        for msg in result.get("messages", []):
            speaker = getattr(msg, "name", "System")
            print(f"\n[{speaker}]")
            print(msg.content)
            print("-" * 60)

        # 메타 정보 출력
        if "current_phase" in result:
            print(f"\n✅ 최종 Phase: {result['current_phase']}")
        if "speaker_counts" in result:
            print(f"📊 발언 횟수: {result['speaker_counts']}")


def main() -> None:
    """CLI 진입점."""
    parser = argparse.ArgumentParser(
        description="TheTable - AI-powered team meeting system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 기본 회의 실행
  python -m thetable "오늘 회의를 시작하겠습니다"

  # 커스텀 프로필 사용
  python -m thetable "회의 시작" --profiles config/custom_profiles.yaml

  # 스트리밍 모드
  python -m thetable "회의 시작" --stream
        """
    )

    parser.add_argument(
        "message",
        help="회의 시작 메시지 (Host가 먼저 말할 내용)"
    )

    parser.add_argument(
        "--profiles",
        "-p",
        help="Agent 프로필 YAML 파일 경로 (기본: config/agent_profiles.yaml)",
    )

    parser.add_argument(
        "--stream",
        "-s",
        action="store_true",
        help="스트리밍 모드 사용 (실시간 출력)",
    )

    args = parser.parse_args()

    # 비동기 실행
    asyncio.run(run_meeting(
        initial_message=args.message,
        profiles_path=args.profiles,
        stream=args.stream,
    ))


if __name__ == "__main__":
    main()
