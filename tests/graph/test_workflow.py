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
    assert result == "participant"


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


def test_workflow_parallel_summarize_process():
    """summarize와 process_response가 병렬로 실행되는 그래프 구조 테스트

    각 에이전트 노드에서 summarize와 process_response로 fan-out되고,
    두 노드 모두 route_next로 fan-in된 후 condition_router로 라우팅되어야 한다.
    """
    from doorae.graph.workflow import create_meeting_workflow

    workflow = create_meeting_workflow()
    graph = workflow.get_graph()

    # 그래프에서 노드 이름 수집
    node_names = {node.name for node in graph.nodes.values()}

    # route_next 패스쓰루 노드가 존재해야 함
    assert "route_next" in node_names, (
        "route_next 패스쓰루 노드가 그래프에 존재해야 합니다"
    )

    # participant 노드가 summarize와 process_response 둘 다로 연결되어야 함
    # (직렬이 아닌 병렬 fan-out)
    edges_by_source = {}
    for edge in graph.edges:
        src = edge.source.name if hasattr(edge.source, 'name') else str(edge.source)
        tgt = edge.target.name if hasattr(edge.target, 'name') else str(edge.target)
        edges_by_source.setdefault(src, set()).add(tgt)

    # summarize → process_response 직렬 엣지가 없어야 함
    summarize_targets = edges_by_source.get("summarize", set())
    assert "process_response" not in summarize_targets, (
        "summarize → process_response 직렬 엣지가 없어야 합니다 (병렬 구조)"
    )

    # summarize와 process_response 모두 route_next로 fan-in
    assert "route_next" in summarize_targets, (
        "summarize → route_next 엣지가 있어야 합니다"
    )
    process_targets = edges_by_source.get("process_response", set())
    assert "route_next" in process_targets, (
        "process_response → route_next 엣지가 있어야 합니다"
    )

    participant_targets = edges_by_source.get("participant", set())
    assert participant_targets == {"summarize", "process_response"}, (
        "participant 노드가 summarize와 process_response로 fan-out해야 합니다"
    )
