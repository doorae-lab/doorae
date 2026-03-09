"""Tests for agenda-based workflow"""
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from doorae.graph.nodes import condition_router
from doorae.graph.state import MeetingState


# 이동된 함수들의 테스트:
# - detect_agenda_completion → ProcessResponseNode._detect_agenda_completion (통합 테스트로 커버)
# - get_remaining_speakers → RefillSpeakersNode._get_remaining_speakers (통합 테스트로 커버)


def test_condition_router_with_pending():
    """큐 있을 때 라우팅 테스트"""
    from langgraph.graph import END

    state: MeetingState = {
        "messages": [],
        "agendas": [{"title": "Test", "status": "pending", "required_speakers": []}],
        "current_agenda_idx": 0,
        "pending_speakers": ["PM", "TechLead"],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = condition_router(state)
    assert result == "pm"  # 첫 번째 pending speaker


def test_condition_router_empty_queue():
    """큐 비었을 때 refill로 라우팅 테스트"""
    state: MeetingState = {
        "messages": [],
        "agendas": [{"title": "Test", "status": "pending", "required_speakers": []}],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = condition_router(state)
    assert result == "refill_speakers"


def test_condition_router_all_agendas_completed():
    """모든 안건 완료 시 END 반환 테스트"""
    from langgraph.graph import END

    state: MeetingState = {
        "messages": [],
        "agendas": [
            {"title": "Agenda 1", "status": "completed", "required_speakers": []},
            {"title": "Agenda 2", "status": "completed", "required_speakers": []},
        ],
        "current_agenda_idx": 2,  # >= len(agendas)
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = condition_router(state)
    assert result == END


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires OpenAI API key - needs Mock update for agenda extraction")
async def test_process_response_basic():
    """process_response 기본 동작 테스트"""
    from doorae.graph.workflow import process_response
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini")

    state: MeetingState = {
        "messages": [
            AIMessage(content="안녕하세요", name="Host"),
        ],
        "agendas": [
            {"title": "Test", "status": "in_progress", "required_speakers": ["Host", "PM"]}
        ],
        "current_agenda_idx": 0,
        "pending_speakers": ["Host"],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    valid_speakers = ["Host", "PM", "TechLead"]
    result = await process_response(state, model, valid_speakers)

    # Host가 pending에서 제거됨
    assert "Host" not in result["pending_speakers"]
    # speaker_counts 업데이트됨
    assert result["speaker_counts"]["Host"] == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires OpenAI API key - needs Mock update for agenda extraction")
async def test_process_response_agenda_completion():
    """안건 완료 처리 테스트"""
    from doorae.graph.workflow import process_response
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini")

    state: MeetingState = {
        "messages": [
            AIMessage(content="좋습니다. 다음 안건으로 넘어가겠습니다", name="Host"),
        ],
        "agendas": [
            {"title": "Agenda 1", "status": "in_progress", "required_speakers": ["Host"]},
            {"title": "Agenda 2", "status": "pending", "required_speakers": ["PM"]},
        ],
        "current_agenda_idx": 0,
        "pending_speakers": ["Host"],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    valid_speakers = ["Host", "PM", "TechLead"]
    result = await process_response(state, model, valid_speakers)

    # 안건 완료 및 인덱스 증가
    assert result["agendas"][0]["status"] == "completed"
    assert result["current_agenda_idx"] == 1
    # pending 초기화
    assert result["pending_speakers"] == []


def test_create_meeting_workflow_integration():
    """create_meeting_workflow 통합 테스트"""
    from doorae.graph.workflow import create_meeting_workflow

    # 워크플로우 생성
    workflow = create_meeting_workflow()

    # 워크플로우가 정상적으로 생성되었는지 확인
    assert workflow is not None
    assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")
