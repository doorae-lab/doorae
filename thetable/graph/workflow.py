"""안건 기반 회의 워크플로우

아키텍처:
- pending_speakers 큐 기반 라우팅 (LLM 호출 최소화)
- 안건(Agenda) 중심의 구조화된 회의 진행
- LLM 기반 멘션 추출 및 의도 분석
- Host 명시적 안건 완료 선언
- AI 자동 안건 관리 (추가/수정/제거)
"""
import asyncio
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from prompt_toolkit import prompt as pt_prompt
from loguru import logger

from thetable.config import get_settings
from thetable.graph.agent_factory import build_agent_node
from thetable.graph.state import MeetingState
from thetable.graph.summarization import summarize_conversation_node
from thetable.core.profile import load_agent_profiles


async def initialize_mcp_tools(config_path: str = None) -> dict[str, list]:
    """MCP tools 초기화 및 서버별 수집

    Args:
        config_path: mcp_servers.json 경로 (None이면 config/mcp_servers.json)

    Returns:
        서버별 tools 딕셔너리 {server_name: [tools]}
    """
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        from thetable.mcp import load_mcp_config, collect_tools_by_server

        # MCP 설정 로드
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "mcp_servers.json"

        config_dict = load_mcp_config(config_path)

        if not config_dict:
            logger.warning("⚠️ 사용 가능한 MCP 서버가 없습니다")
            return {}

        # MCP 클라이언트 초기화
        mcp_client = MultiServerMCPClient(config_dict)

        # 모든 서버의 tools 수집
        server_names = set(config_dict.keys())
        tools_by_server = await collect_tools_by_server(mcp_client, server_names)

        total = sum(len(t) for t in tools_by_server.values())
        logger.info(f"✅ MCP 도구 로드 완료: {total}개 도구 ({len(tools_by_server)}개 서버)")

        return tools_by_server

    except ImportError:
        logger.warning("⚠️ langchain-mcp-adapters가 설치되지 않았습니다")
        return {}
    except FileNotFoundError:
        logger.warning(f"⚠️ MCP 설정 파일을 찾을 수 없습니다: {config_path}")
        return {}
    except Exception as e:
        logger.error(f"⚠️ MCP 초기화 실패: {e}")
        return {}


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
    
    logger.debug(f"멘션 추출 LLM 응답: '{result}' (발언: {content[:50]}...)")

    if result == "없음":
        return []

    extracted = [s.strip() for s in result.split(',') if s.strip() in valid_speakers]
    logger.debug(f"추출된 발화자: {extracted}")
    return extracted


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
        "오늘 회의는 여기까지", "회의 종료합니다"
    ]
    result = any(kw in content for kw in end_keywords)
    if result:
        logger.debug(f"회의 종료 키워드 감지됨: {content[:50]}...")
    return result


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
            import time as time_module
            new_agendas[current_idx]["status"] = "completed"
            new_agendas[current_idx]["end_time"] = time_module.time()
            new_idx = current_idx + 1
            # 다음 안건 시작 시간 설정
            if new_idx < len(new_agendas):
                new_agendas[new_idx]["status"] = "in_progress"
                new_agendas[new_idx]["start_time"] = time_module.time()
            new_pending = []  # 안건 변경 시 pending 초기화

    # 6. Host 회의 종료 발언 감지 (안건 상태 무관)
    if speaker_name == "Host":
        # 1단계: 키워드 감지 (최우선, 안건 상태 무관)
        if detect_meeting_end_keyword(content):
            meeting_ended = True
        
        # 2단계: LLM 분석 (키워드 미감지 + 안건 대부분 완료)
        elif len(new_agendas) > 0:
            completed_count = sum(1 for a in new_agendas 
                                if a["status"] in ["completed", "deferred"])
            completion_rate = completed_count / len(new_agendas)
            
            # 80% 이상 완료 시에만 LLM 분석 (토큰 절약)
            if completion_rate >= 0.8:
                meeting_ended = await detect_meeting_end_llm(content, model)

    # 턴 카운트 증가
    turn_count = state.get("turn_count", 0) + 1

    # 7. 안건 동적 업데이트 (매 발언마다)
    from thetable.graph.agenda_manager import extract_agenda_updates

    try:
        # 최근 10개 메시지만 분석 (토큰 절약)
        recent_messages = messages[-10:] if len(messages) > 10 else messages

        agenda_result = await extract_agenda_updates(
            llm=model,
            messages=recent_messages,
            current_items=new_agendas,
        )

        # 업데이트된 안건으로 교체 (타임스탬프 보존)
        # agenda_result가 None이거나 items가 없으면 기존 안건 유지
        if agenda_result is None:
            logger.warning("안건 추출 결과가 None, 기존 안건 유지")
        else:
            # AgendaItem 리스트를 dict 리스트로 변환
            new_agendas_from_llm = agenda_result.items_as_dicts()
            
            # 빈 리스트가 반환되면 기존 안건 유지 (중요!)
            if not new_agendas_from_llm:
                logger.warning("안건 추출 결과가 비어있어 기존 안건 유지")
            else:
                # 기존 타임스탬프 및 필수 정보 복원 (LLM이 제거했을 수 있음)
                for i, new_agenda in enumerate(new_agendas_from_llm):
                    if i < len(new_agendas):
                        old_agenda = new_agendas[i]
                        
                        # 1. 필수 필드 보존 (새 안건에 없으면 기존 값 유지)
                        if not new_agenda.get("required_speakers") and old_agenda.get("required_speakers"):
                            new_agenda["required_speakers"] = old_agenda["required_speakers"]
                            
                        if not new_agenda.get("description") and old_agenda.get("description"):
                            new_agenda["description"] = old_agenda["description"]
                            
                        if not new_agenda.get("owner") and old_agenda.get("owner"):
                            new_agenda["owner"] = old_agenda["owner"]

                        # 2. 시스템 관리 필드 보존 (start_time, end_time)
                        if old_agenda.get("start_time"):
                            new_agenda["start_time"] = old_agenda["start_time"]
                        if old_agenda.get("end_time"):
                            new_agenda["end_time"] = old_agenda["end_time"]

                new_agendas = new_agendas_from_llm

    except Exception as e:
        # 안건 업데이트 실패 시 기존 안건 유지
        print(f"⚠️ 안건 업데이트 실패: {e}")

    return {
        "pending_speakers": new_pending,
        "speaker_counts": new_counts,
        "current_agenda_idx": new_idx,
        "agendas": new_agendas,
        "consecutive_host_delegations": 0,  # 정상 진행 시 리셋
        "turn_count": turn_count,
        "meeting_ended": meeting_ended,
    }


async def refill_speakers(state: MeetingState, model, valid_speakers: list[str] = None) -> dict:
    """pending_speakers 비었을 때 채우기"""
    agendas = state.get("agendas", [])
    current_idx = state.get("current_agenda_idx", 0)
    speaker_counts = state.get("speaker_counts", {})
    consecutive = state.get("consecutive_host_delegations", 0)

    if current_idx >= len(agendas):
        return {"pending_speakers": []}  # 모든 안건 완료

    current_agenda = agendas[current_idx]
    required = current_agenda.get("required_speakers", [])
    
    # 실제 존재하는 에이전트만 필터링 (Designer, DevOps 등 없는 에이전트 무시)
    if valid_speakers:
        valid_required = [s for s in required if s in valid_speakers]
        logger.debug(f"refill_speakers: required={required}, valid_required={valid_required}")
    else:
        valid_required = required

    # 1차: 안건의 required_speakers 중 미발언자
    already_spoken = set(speaker_counts.keys())
    remaining = get_remaining_speakers(valid_required, already_spoken)
    
    logger.debug(f"refill_speakers: already_spoken={already_spoken}, remaining={remaining}")

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

    logger.debug(f"condition_router: pending={pending}, meeting_ended={meeting_ended}, turn={turn_count}/{max_turns}, idx={current_idx}/{len(agendas)}")

    # 회의 종료 플래그 최우선 체크
    if meeting_ended:
        logger.debug("condition_router: END (meeting_ended)")
        return END

    # 최대 턴 수 초과 체크 (무한루프 방지)
    if turn_count >= max_turns:
        logger.debug("condition_router: END (max_turns)")
        return END

    # 모든 안건 완료 체크
    if current_idx >= len(agendas):
        logger.debug("condition_router: END (all agendas done)")
        return END

    if pending:
        next_speaker = pending[0].lower()
        logger.debug(f"condition_router: routing to '{next_speaker}'")
        return next_speaker

    # 빈 큐 → refill_speakers 노드로
    logger.debug("condition_router: routing to 'refill_speakers'")
    return "refill_speakers"


def create_meeting_workflow(
    profiles_path: str = "config/agent_profiles.yaml",
    main_model = None,  # BaseChatModel
    task_model = None,  # BaseChatModel
    mcp_tools: dict[str, list] = None
):
    """안건 기반 회의 워크플로우 생성

    Args:
        profiles_path: agent_profiles.yaml 경로
        main_model: 회의 에이전트 응답 생성용 LLM (None이면 기본 모델 생성)
        task_model: 작은 작업용 LLM (None이면 기본 모델 생성)
        mcp_tools: 서버별 MCP tools 딕셔너리 {server_name: [tools]}

    Returns:
        CompiledGraph: 실행 가능한 회의 그래프
    """

    settings = get_settings()
    
    # Main model (에이전트 응답 생성용)
    if main_model is None:
        main_kwargs = {
            "temperature": settings.llm_main_temperature,
            "max_tokens": settings.llm_main_max_tokens,
            "streaming": True,
            "timeout": settings.llm_timeout,
            "max_retries": settings.llm_max_retries,
        }
        if settings.openai_api_key:
            main_kwargs["api_key"] = settings.openai_api_key
        if settings.openai_base_url:
            main_kwargs["base_url"] = settings.openai_base_url
            
        main_model = init_chat_model(
            model=settings.llm_main_model,
            model_provider=settings.llm_main_provider,
            **main_kwargs
        )
    
    # Task model (유틸리티 작업용)
    if task_model is None:
        task_kwargs = {
            "temperature": settings.llm_task_temperature,
            "max_tokens": settings.llm_task_max_tokens,
            "timeout": settings.llm_timeout,
            "max_retries": settings.llm_max_retries,
        }
        if settings.openai_api_key:
            task_kwargs["api_key"] = settings.openai_api_key
        if settings.openai_base_url:
            task_kwargs["base_url"] = settings.openai_base_url
            
        task_model = init_chat_model(
            model=settings.llm_task_model,
            model_provider=settings.llm_task_provider,
            **task_kwargs
        )

    # 1. 프로필 로드
    profiles = load_agent_profiles(profiles_path)

    # 2. StateGraph 생성
    workflow = StateGraph(MeetingState)

    # 3. refill_speakers 노드 추가 (main_model 사용)
    async def refill_with_model(state: MeetingState):
        return await refill_speakers(state, main_model, list(profiles.keys()))
    
    workflow.add_node("refill_speakers", refill_with_model)

    # 4. summarize 노드 추가 (task_model 사용)
    async def summarize_with_model(state: MeetingState):
        return await summarize_conversation_node(state, task_model)

    workflow.add_node("summarize", summarize_with_model)

    # 5. process_response 노드 추가 (task_model 사용)
    async def process_with_model(state: MeetingState):
        return await process_response(state, task_model, list(profiles.keys()))

    workflow.add_node("process_response", process_with_model)

    # 5. 각 에이전트 노드 추가 (is_human 분기)
    for name, profile in profiles.items():
        if profile.is_human:
            # 사용자 참여자는 입력 노드 생성
            node = create_human_node(profile)
        else:
            # Agent별 MCP tools 필터링
            agent_tools = []
            if mcp_tools and profile.mcp_tools:
                for server_name in profile.mcp_tools:
                    if server_name in mcp_tools:
                        agent_tools.extend(mcp_tools[server_name])

                if agent_tools:
                    logger.info(f"✅ {profile.name}: {len(agent_tools)}개 MCP 도구 연결 (서버: {', '.join(profile.mcp_tools)})")
                else:
                    logger.warning(f"⚠️ {profile.name}: MCP 도구 설정됨({profile.mcp_tools}) 그러나 로드된 도구 없음 (mcp_tools keys: {list(mcp_tools.keys()) if mcp_tools else 'None'})")

            # AI 에이전트는 기존 로직 사용 (main_model + agent별 tools)
            node = build_agent_node(
                profile,
                main_model,
                agent_tools if agent_tools else None,
                list(profiles.keys()),
                profiles
            )
        workflow.add_node(name.lower(), node)

    # 6. 진입점: refill_speakers
    workflow.set_entry_point("refill_speakers")

    # 7. 에이전트 → summarize → process_response
    for name in profiles.keys():
        workflow.add_edge(name.lower(), "summarize")

    workflow.add_edge("summarize", "process_response")

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






