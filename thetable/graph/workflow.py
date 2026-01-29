"""Meeting workflow using langgraph-supervisor

단순화된 구조:
- Host가 Phase 규칙을 프롬프트로 이해
- PhaseController 불필요 (Host가 직접 Phase 전환 판단)
- 단일 그래프로 처리 (Phase 래퍼 불필요)
"""
import re
from typing import Dict
from langchain_openai import ChatOpenAI
from langgraph_supervisor import create_supervisor

from thetable.graph.agent_factory import build_agent_graph
from thetable.graph.state import MeetingState
from thetable.core.profile import load_agent_profiles


HOST_PROMPT = """You are the meeting Host responsible for phase management.

## Current State
- Phase: {current_phase}
- Speaker counts: {speaker_counts}
- Phase history: {phase_history}

## Phase Rules
1. **opening**: Greet participants and introduce the meeting agenda.
   - Transition condition: After greeting, move to status_check
   
2. **status_check**: PM must report project status.
   - Required speakers: PM
   - Transition condition: After PM speaks, move to issue_resolution
   
3. **issue_resolution**: TechLead addresses technical issues.
   - TechLead can delegate to Backend/Frontend/DevOps experts as needed
   - Transition condition: After issues resolved, move to closing
   
4. **closing**: Summarize key decisions and action items.
   - Transition condition: After summary, END meeting

## Instructions
- Check speaker_counts to ensure required speakers have participated
- Update current_phase when transition conditions are met
- Direct agents based on their expertise and current phase needs
- Respond in Korean

**When transitioning phases, include in your response:**
[PHASE: next_phase_name]

**Example:**
"PM님의 상태 보고를 들었습니다. 이제 기술적 이슈를 논의하겠습니다. [PHASE: issue_resolution]"
"""


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    model: ChatOpenAI = None
) -> object:
    """langgraph-supervisor 기반 회의 워크플로우 생성
    
    Args:
        profiles_path: agent_profiles.yaml 경로
        model: LLM 모델 (None이면 기본 모델 생성)
        
    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """
    
    if model is None:
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # 1. 프로필 로드
    profiles = load_agent_profiles(profiles_path)
    
    # 2. 각 에이전트 그래프 빌드 (계층적)
    agent_graphs = []
    for name, profile in profiles.items():
        if name != "Host":  # Host는 supervisor로 사용
            agent_graph = build_agent_graph(profile, model)
            agent_graphs.append(agent_graph)
    
    # 3. 최상위 supervisor 생성 - Host가 Phase도 관리
    meeting_supervisor = create_supervisor(
        agents=agent_graphs,
        model=model,
        supervisor_name="Host",
        prompt=HOST_PROMPT,
        state_schema=MeetingState  # 확장된 상태 사용
    )
    
    # 4. 컴파일 (Phase 래퍼 불필요!)
    workflow = meeting_supervisor.compile()
    
    # 5. Phase 전환 후처리 추가 (선택적)
    workflow = add_phase_transition_handler(workflow)
    
    return workflow


def add_phase_transition_handler(workflow):
    """Host 응답에서 Phase 전환 감지 및 상태 업데이트
    
    Note: langgraph-supervisor의 메시지 처리 후 호출되는 후처리 핸들러
    """
    
    def process_host_response(state: MeetingState) -> dict:
        """Host 응답 분석하여 Phase 업데이트"""
        if not state.get("messages"):
            return {}
        
        last_message = state["messages"][-1]
        
        # [PHASE: phase_name] 형식 파싱
        if "[PHASE:" in last_message.content:
            match = re.search(r'\[PHASE:\s*(\w+)\]', last_message.content)
            if match:
                new_phase = match.group(1)
                current_phase = state.get("current_phase", "opening")
                
                return {
                    "current_phase": new_phase,
                    "phase_history": state.get("phase_history", []) + [current_phase]
                }
        
        return {}
    
    # 워크플로우에 후처리 핸들러 등록
    # Note: langgraph-supervisor v0.0.1+에서 지원 예정
    # 현재는 Host 프롬프트에서 Phase 전환 처리
    
    return workflow


def validate_phase_transition(state: MeetingState, new_phase: str) -> bool:
    """Phase 전환 조건 검증
    
    Args:
        state: 현재 회의 상태
        new_phase: 전환하려는 Phase
        
    Returns:
        bool: 전환 가능 여부
    """
    current_phase = state.get("current_phase", "opening")
    speaker_counts = state.get("speaker_counts", {})
    
    # Phase별 전환 조건
    transitions = {
        "opening": {
            "next": "status_check",
            "condition": lambda: True  # 항상 가능
        },
        "status_check": {
            "next": "issue_resolution",
            "condition": lambda: speaker_counts.get("PM", 0) > 0
        },
        "issue_resolution": {
            "next": "closing",
            "condition": lambda: speaker_counts.get("TechLead", 0) > 0
        },
        "closing": {
            "next": "END",
            "condition": lambda: True
        }
    }
    
    rule = transitions.get(current_phase)
    if not rule:
        return False
    
    if rule["next"] != new_phase:
        return False
    
    return rule["condition"]()
