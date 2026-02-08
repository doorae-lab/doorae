"""안건 기반 회의 워크플로우 실행 예제"""
import asyncio
import time
from thetable.graph.workflow import create_meeting_workflow
from thetable.core.profile import load_agent_profiles


async def main():
    """안건 기반 회의 실행"""

    # 활성 에이전트 로드
    profiles = load_agent_profiles()
    agent_names = list(profiles.keys())
    non_host_agents = [name for name in agent_names if name != "Host"]

    # 안건별 핵심 담당자 선정
    tech_lead = ["TechLead"] if "TechLead" in agent_names else (non_host_agents[:1] if non_host_agents else [])
    pm = ["PM"] if "PM" in agent_names else (non_host_agents[:1] if non_host_agents else [])

    # 초기 상태 설정 (핵심 담당자만 required, 나머지는 멘션으로 발언 가능)
    initial_state = {
        "messages": [],
        "agendas": [
            {
                "title": "회의 시작 및 현황 공유",
                "description": "오늘 회의를 시작하고 주간 현황을 공유합니다",
                "status": "pending",
                "required_speakers": ["Host"] + (pm if pm else non_host_agents[:1])
            },
            {
                "title": "결제 시스템 오류 대응",
                "description": "지난주 발생한 결제 실패 이슈의 원인 분석 및 해결 방안 논의",
                "status": "pending",
                "required_speakers": tech_lead  # 기술 이슈이므로 TechLead만 필수
            },
            {
                "title": "신규 기능 배포 일정",
                "description": "다음 스프린트에 배포할 기능들의 우선순위와 일정 조율",
                "status": "pending",
                "required_speakers": pm  # 일정 관리이므로 PM만 필수
            },
            {
                "title": "회의 마무리",
                "description": "논의 내용 정리 및 액션 아이템 확정",
                "status": "pending",
                "required_speakers": ["Host"]
            },
        ],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": time.time(),
    }
    
    # 워크플로우 생성
    workflow = create_meeting_workflow()
    
    print("=" * 80)
    print("안건 기반 회의 시작")
    print("=" * 80)
    
    # 워크플로우 실행
    async for event in workflow.astream(initial_state):
        for node_name, node_output in event.items():
            if "messages" in node_output and node_output["messages"]:
                last_message = node_output["messages"][-1]
                speaker = getattr(last_message, 'name', 'Unknown')
                content = getattr(last_message, 'content', '')
                
                # 현재 안건 정보 표시
                current_idx = node_output.get("current_agenda_idx", 0)
                agendas = node_output.get("agendas", [])
                
                if current_idx < len(agendas):
                    current_agenda = agendas[current_idx]
                    print(f"\n[안건 {current_idx + 1}: {current_agenda['title']}]")
                
                print(f"\n{speaker}: {content}")
                print("-" * 80)
                
                # pending_speakers 상태 표시
                pending = node_output.get("pending_speakers", [])
                if pending:
                    print(f"다음 발언 예정: {', '.join(pending)}")
    
    print("\n" + "=" * 80)
    print("회의 종료")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
