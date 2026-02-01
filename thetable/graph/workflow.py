"""안건 기반 회의 워크플로우

아키텍처:
- pending_speakers 큐 기반 라우팅 (LLM 호출 최소화)
- 안건(Agenda) 중심의 구조화된 회의 진행
- 하이브리드 멘션 추출 (규칙 기반 + LLM 보조)
- Host 명시적 안건 완료 선언
"""
import asyncio
import re
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from prompt_toolkit import prompt as pt_prompt

from thetable.config import get_settings
from thetable.graph.agent_factory import build_agent_node
from thetable.graph.state import MeetingState
from thetable.core.profile import load_agent_profiles


def extract_mentions_rule_based(content: str, valid_speakers: list[str]) -> list[str]:
    """규칙 기반 멘션 추출"""
    mentions = []
    patterns = [
        r'@(\w+)',              # @PM, @Designer
        r'(\w+)님',             # PM님, Designer님
        r'(\w+)\s*(의견|검토|확인)',  # PM 의견, TechLead 검토
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            name = match[0] if isinstance(match, tuple) else match
            # valid_speakers에서 매칭
            for speaker in valid_speakers:
                if speaker.lower() == name.lower():
                    mentions.append(speaker)

    return list(set(mentions))


def create_human_node(profile):
    """사용자 입력 노드 생성
    
    Args:
        profile: AgentProfile 객체 (is_human=True)
    
    Returns:
        사용자 입력을 받는 노드 함수
    """
    async def human_node(state: MeetingState) -> dict:
        """사용자 입력 대기 및 메시지 추가"""
        messages = state.get("messages", [])
        agendas = state.get("agendas", [])
        current_idx = state.get("current_agenda_idx", 0)
        
        # 현재 안건 정보 표시
        print(f"\n{'='*60}", flush=True)
        print(f"[{profile.name}님 차례입니다]", flush=True)
        
        if current_idx < len(agendas):
            current_agenda = agendas[current_idx]
            print(f"\n📋 현재 안건: {current_agenda.get('title', 'N/A')}", flush=True)
            print(f"   설명: {current_agenda.get('description', 'N/A')}", flush=True)
        
        # 최근 발언 표시 (최대 3개)
        if messages:
            print(f"\n💬 최근 발언:", flush=True)
            recent_messages = messages[-3:]
            for msg in recent_messages:
                speaker = getattr(msg, 'name', 'Unknown')
                content = getattr(msg, 'content', '')
                # 길면 첫 100자만 표시
                display_content = content[:100] + "..." if len(content) > 100 else content
                print(f"   [{speaker}] {display_content}", flush=True)
        
        print(f"\n{'='*60}", flush=True)
        print(f"💡 의견을 입력하세요 (빈 입력 시 스킵):", flush=True)
        
        # prompt_toolkit을 사용하여 한글 UTF-8 인코딩 문제 해결
        # asyncio.to_thread로 감싸서 비동기 처리
        user_input = await asyncio.to_thread(pt_prompt, "> ")
        
        # 빈 입력 시 스킵
        if not user_input.strip():
            print(f"[{profile.name}님이 스킵했습니다]\n", flush=True)
            # 빈 메시지 추가 (스킵 표시용)
            skip_message = HumanMessage(
                content="(발언 없음)",
                name=profile.name
            )
            return {"messages": [skip_message]}
        
        # 사용자 입력을 메시지로 추가
        user_message = HumanMessage(
            content=user_input,
            name=profile.name
        )
        
        return {"messages": [user_message]}
    
    return human_node


async def extract_mentions_llm(content: str, model, valid_speakers: list[str]) -> list[str]:
    """LLM 기반 의도 추출 (규칙 실패 시)"""
    prompt = f"""다음 발언에서 언급하거나 의견을 요청하는 참여자를 추출하세요.

발언: "{content}"

선택 가능한 참여자: {', '.join(valid_speakers)}

언급된 참여자 이름만 쉼표로 구분하여 출력 (없으면 "없음"):"""

    response = await model.ainvoke(prompt)
    result = response.content.strip()

    if result == "없음":
        return []

    return [s.strip() for s in result.split(',') if s.strip() in valid_speakers]


def detect_agenda_completion(content: str) -> bool:
    """Host 발언에서 안건 완료 키워드 감지"""
    completion_keywords = [
        "다음 안건", "다음으로", "넘어가",
        "마무리", "정리하면", "결론",
        "이 안건은 여기까지"
    ]
    return any(kw in content for kw in completion_keywords)


def detect_meeting_end_keyword(content: str) -> bool:
    """Host 발언에서 회의 종료 키워드 감지"""
    end_keywords = [
        "회의를 마치겠습니다", "회의를 종료", "이상으로 마치겠습니다",
        "오늘 회의는 여기까지", "수고하셨습니다", "회의 종료"
    ]
    return any(kw in content for kw in end_keywords)


async def detect_meeting_end_llm(content: str, model) -> bool:
    """LLM으로 회의 종료 의도 분석 (키워드 미감지 시 fallback)"""
    prompt = f"""다음 Host의 발언이 회의를 종료하려는 의도인지 판단하세요.

발언: "{content}"

회의 종료 의도가 명확하면 "예", 아니면 "아니오"로만 답하세요:"""

    response = await model.ainvoke(prompt)
    result = response.content.strip()
    
    return result == "예"


def get_remaining_speakers(required_speakers: list[str], already_spoken: set) -> list[str]:
    """안건의 required_speakers 중 아직 발언하지 않은 참여자 반환"""
    return [s for s in required_speakers if s not in already_spoken]


async def process_response(state: MeetingState, model, valid_speakers: list[str]) -> dict:
    """에이전트 응답 처리"""
    messages = state.get("messages", [])
    pending = state.get("pending_speakers", [])
    speaker_counts = state.get("speaker_counts", {})
    agendas = state.get("agendas", [])
    current_idx = state.get("current_agenda_idx", 0)

    if not messages:
        return {}

    last_msg = messages[-1]
    speaker_name = getattr(last_msg, 'name', '')
    content = getattr(last_msg, 'content', '')

    # 1. 현재 발언자를 pending에서 제거
    new_pending = [s for s in pending if s != speaker_name]

    # 2. speaker_counts 업데이트
    new_counts = speaker_counts.copy()
    new_counts[speaker_name] = new_counts.get(speaker_name, 0) + 1

    # 3. 멘션 추출 (LLM 기반)
    # valid_speakers는 파라미터로 전달됨
    # 규칙 기반은 주석 처리 - LLM만 사용
    # mentions = extract_mentions_rule_based(content, valid_speakers)
    # if not mentions and speaker_name != "Host":
    #     mentions = await extract_mentions_llm(content, model, valid_speakers)
    
    # LLM이 직접 판단
    mentions = await extract_mentions_llm(content, model, valid_speakers)

    # 4. 새 멘션을 pending에 추가 (중복 제외)
    for m in mentions:
        if m not in new_pending and m != speaker_name:
            new_pending.append(m)

    # 5. Host 발언이면 안건 완료 체크
    new_idx = current_idx
    new_agendas = agendas.copy()
    meeting_ended = False

    if speaker_name == "Host" and detect_agenda_completion(content):
        if current_idx < len(new_agendas):
            new_agendas[current_idx]["status"] = "completed"
            new_idx = current_idx + 1
            new_pending = []  # 안건 변경 시 pending 초기화

    # 6. 마지막 안건에서 Host 회의 종료 발언 감지
    if speaker_name == "Host" and current_idx == len(agendas) - 1:
        # 키워드 우선 감지
        if detect_meeting_end_keyword(content):
            meeting_ended = True
        # 키워드 미감지 시 LLM 분석
        elif await detect_meeting_end_llm(content, model):
            meeting_ended = True

    # 턴 카운트 증가
    turn_count = state.get("turn_count", 0) + 1

    return {
        "pending_speakers": new_pending,
        "speaker_counts": new_counts,
        "current_agenda_idx": new_idx,
        "agendas": new_agendas,
        "consecutive_host_delegations": 0,  # 정상 진행 시 리셋
        "turn_count": turn_count,
        "meeting_ended": meeting_ended,
    }


async def refill_speakers(state: MeetingState, model) -> dict:
    """pending_speakers 비었을 때 채우기"""
    agendas = state.get("agendas", [])
    current_idx = state.get("current_agenda_idx", 0)
    speaker_counts = state.get("speaker_counts", {})
    consecutive = state.get("consecutive_host_delegations", 0)

    if current_idx >= len(agendas):
        return {"pending_speakers": []}  # 모든 안건 완료

    current_agenda = agendas[current_idx]
    required = current_agenda.get("required_speakers", [])

    # 1차: 안건의 required_speakers 중 미발언자
    already_spoken = set(speaker_counts.keys())
    remaining = get_remaining_speakers(required, already_spoken)

    if remaining:
        return {
            "pending_speakers": remaining[:2],  # 최대 2명씩
            "consecutive_host_delegations": 0,
        }

    # 2차: Host 위임 (무한루프 방지)
    if consecutive >= 3:
        # 강제로 Host가 마무리하도록
        return {
            "pending_speakers": ["Host"],
            "consecutive_host_delegations": 0,
        }

    return {
        "pending_speakers": ["Host"],
        "consecutive_host_delegations": consecutive + 1,
    }


def condition_router(state: MeetingState) -> str:
    """pending_speakers 기반 라우팅 (LLM 없음)"""
    pending = state.get("pending_speakers", [])
    agendas = state.get("agendas", [])
    current_idx = state.get("current_agenda_idx", 0)
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 30)
    meeting_ended = state.get("meeting_ended", False)

    # 회의 종료 플래그 최우선 체크
    if meeting_ended:
        return END

    # 최대 턴 수 초과 체크 (무한루프 방지)
    if turn_count >= max_turns:
        return END

    # 모든 안건 완료 체크
    if current_idx >= len(agendas):
        return END

    if pending:
        return pending[0].lower()

    # 빈 큐 → refill_speakers 노드로
    return "refill_speakers"


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    model: ChatOpenAI = None
):
    """안건 기반 회의 워크플로우 생성

    Args:
        profiles_path: agent_profiles.yaml 경로
        model: LLM 모델 (None이면 기본 모델 생성)

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """

    if model is None:
        settings = get_settings()
        kwargs = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "api_key": settings.openai_api_key,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        # 스트리밍 활성화
        kwargs["streaming"] = True
        model = ChatOpenAI(**kwargs)

    # 1. 프로필 로드
    profiles = load_agent_profiles(profiles_path)

    # 2. StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 3. refill_speakers 노드 추가
    async def refill_with_model(state: MeetingState):
        return await refill_speakers(state, model)
    
    workflow.add_node("refill_speakers", refill_with_model)

    # 4. process_response 노드 추가
    async def process_with_model(state: MeetingState):
        return await process_response(state, model, list(profiles.keys()))
    
    workflow.add_node("process_response", process_with_model)

    # 5. 각 에이전트 노드 추가 (is_human 분기)
    for name, profile in profiles.items():
        if profile.is_human:
            # 사용자 참여자는 입력 노드 생성
            node = create_human_node(profile)
        else:
            # AI 에이전트는 기존 로직 사용
            node = build_agent_node(profile, model, list(profiles.keys()), profiles)
        workflow.add_node(name.lower(), node)

    # 6. 진입점: refill_speakers
    workflow.set_entry_point("refill_speakers")

    # 7. 에이전트 → process_response
    for name in profiles.keys():
        workflow.add_edge(name.lower(), "process_response")

    # 8. process_response → condition_router
    available_targets = {name.lower(): name.lower() for name in profiles.keys()}
    available_targets["refill_speakers"] = "refill_speakers"
    available_targets[END] = END

    workflow.add_conditional_edges(
        "process_response",
        condition_router,
        available_targets
    )

    # 9. refill_speakers → condition_router
    workflow.add_conditional_edges(
        "refill_speakers",
        condition_router,
        available_targets
    )

    # 10. 컴파일
    return workflow.compile()






