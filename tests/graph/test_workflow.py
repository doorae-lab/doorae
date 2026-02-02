"""Tests for agenda-based workflow"""
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from thetable.graph.workflow import (
    extract_mentions_rule_based,
    detect_agenda_completion,
    get_remaining_speakers,
    condition_router,
)
from thetable.graph.state import MeetingState


def test_extract_mentions_rule_based():
    """정규식 멘션 추출 테스트"""
    valid_speakers = ["Host", "PM", "Designer", "TechLead", "DevOps"]

    # @멘션 테스트
    content1 = "@PM님 의견 부탁드립니다"
    assert "PM" in extract_mentions_rule_based(content1, valid_speakers)

    # 님 호칭 테스트
    content2 = "Designer님, TechLead님 확인 부탁드립니다"
    mentions2 = extract_mentions_rule_based(content2, valid_speakers)
    assert "Designer" in mentions2
    assert "TechLead" in mentions2

    # 의견/검토/확인 패턴 테스트
    content3 = "PM 의견도 필요합니다"
    assert "PM" in extract_mentions_rule_based(content3, valid_speakers)

    # 멘션 없음
    content4 = "저는 이렇게 생각합니다"
    assert extract_mentions_rule_based(content4, valid_speakers) == []


def test_detect_agenda_completion():
    """안건 완료 키워드 감지 테스트"""
    assert detect_agenda_completion("다음 안건으로 넘어가겠습니다") is True
    assert detect_agenda_completion("이제 마무리하겠습니다") is True
    assert detect_agenda_completion("정리하면 이렇습니다") is True
    assert detect_agenda_completion("이 안건은 여기까지입니다") is True
    assert detect_agenda_completion("계속 논의하겠습니다") is False
    assert detect_agenda_completion("의견 감사합니다") is False


def test_get_remaining_speakers():
    """미발언자 추출 테스트"""
    required = ["Host", "PM", "Designer"]
    already_spoken = {"Host"}

    remaining = get_remaining_speakers(required, already_spoken)
    assert "Host" not in remaining
    assert "PM" in remaining
    assert "Designer" in remaining

    # 모두 발언한 경우
    all_spoken = {"Host", "PM", "Designer"}
    remaining2 = get_remaining_speakers(required, all_spoken)
    assert remaining2 == []


def test_condition_router_with_pending():
    """큐 있을 때 라우팅 테스트"""
    from langgraph.graph import END

    state: MeetingState = {
        "messages": [],
        "agendas": [{"title": "Test", "status": "pending", "required_speakers": []}],
        "current_agenda_idx": 0,
        "pending_speakers": ["PM", "Designer"],
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
    from thetable.graph.workflow import process_response
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

    valid_speakers = ["Host", "PM", "Designer", "TechLead", "DevOps"]
    result = await process_response(state, model, valid_speakers)

    # Host가 pending에서 제거됨
    assert "Host" not in result["pending_speakers"]
    # speaker_counts 업데이트됨
    assert result["speaker_counts"]["Host"] == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires OpenAI API key - needs Mock update for agenda extraction")
async def test_process_response_agenda_completion():
    """안건 완료 처리 테스트"""
    from thetable.graph.workflow import process_response
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

    valid_speakers = ["Host", "PM", "Designer", "TechLead", "DevOps"]
    result = await process_response(state, model, valid_speakers)

    # 안건 완료 및 인덱스 증가
    assert result["agendas"][0]["status"] == "completed"
    assert result["current_agenda_idx"] == 1
    # pending 초기화
    assert result["pending_speakers"] == []


@pytest.mark.asyncio
async def test_refill_speakers_with_remaining():
    """미발언자 있을 때 refill 테스트"""
    from thetable.graph.workflow import refill_speakers
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini")

    state: MeetingState = {
        "messages": [],
        "agendas": [
            {
                "title": "Test",
                "status": "in_progress",
                "required_speakers": ["Host", "PM", "Designer"],
            }
        ],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {"Host": 1},  # Host만 발언함
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = await refill_speakers(state, model)

    # PM, Designer 중 최대 2명 반환
    assert len(result["pending_speakers"]) <= 2
    assert all(s in ["PM", "Designer"] for s in result["pending_speakers"])


@pytest.mark.asyncio
async def test_refill_speakers_host_delegation():
    """모두 발언 후 Host 위임 테스트"""
    from thetable.graph.workflow import refill_speakers
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini")

    state: MeetingState = {
        "messages": [],
        "agendas": [
            {
                "title": "Test",
                "status": "in_progress",
                "required_speakers": ["PM", "Designer"],
            }
        ],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {"PM": 1, "Designer": 1},  # 모두 발언함
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = await refill_speakers(state, model)

    # Host에게 위임
    assert result["pending_speakers"] == ["Host"]
    assert result["consecutive_host_delegations"] == 1


@pytest.mark.asyncio
async def test_infinite_loop_prevention():
    """무한루프 방지 테스트 (3회 제한)"""
    from thetable.graph.workflow import refill_speakers
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model="gpt-4o-mini")

    state: MeetingState = {
        "messages": [],
        "agendas": [
            {
                "title": "Test",
                "status": "in_progress",
                "required_speakers": ["PM"],
            }
        ],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {"PM": 1},
        "consecutive_host_delegations": 3,  # 이미 3회
        "start_time": 0.0,
    }

    result = await refill_speakers(state, model)

    # 강제로 Host 선택 및 카운터 리셋
    assert result["pending_speakers"] == ["Host"]
    assert result["consecutive_host_delegations"] == 0


def test_create_human_node():
    """create_human_node 함수 테스트"""
    from thetable.graph.workflow import create_human_node
    from thetable.core.profile import AgentProfile

    # Human 프로필 생성
    human_profile = AgentProfile(
        name="TestUser",
        role="test_role",
        responsibilities=["Test"],
        expertise=["Testing"],
        is_human=True
    )

    # Human 노드 생성
    node = create_human_node(human_profile)

    # 노드가 함수인지 확인
    assert callable(node)


@pytest.mark.asyncio
async def test_human_node_skip_empty_input(monkeypatch):
    """Human 노드 빈 입력 시 스킵 테스트"""
    from thetable.graph.workflow import create_human_node
    from thetable.core.profile import AgentProfile
    import asyncio

    # 빈 입력 시뮬레이션
    async def mock_input(*args, **kwargs):
        return ""

    monkeypatch.setattr(asyncio, "to_thread", lambda fn, *args: mock_input())

    human_profile = AgentProfile(
        name="TestUser",
        role="test_role",
        responsibilities=["Test"],
        expertise=["Testing"],
        is_human=True
    )

    node = create_human_node(human_profile)

    state: MeetingState = {
        "messages": [],
        "agendas": [],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = await node(state)

    # 빈 입력 시 스킵 메시지 추가
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "(발언 없음)"
    assert result["messages"][0].name == "TestUser"


@pytest.mark.asyncio
async def test_human_node_with_user_input(monkeypatch):
    """Human 노드 사용자 입력 테스트"""
    from thetable.graph.workflow import create_human_node
    from thetable.core.profile import AgentProfile
    import asyncio

    # 사용자 입력 시뮬레이션
    test_input = "테스트 의견입니다"
    async def mock_input(*args, **kwargs):
        return test_input

    monkeypatch.setattr(asyncio, "to_thread", lambda fn, *args: mock_input())

    human_profile = AgentProfile(
        name="TestUser",
        role="test_role",
        responsibilities=["Test"],
        expertise=["Testing"],
        is_human=True
    )

    node = create_human_node(human_profile)

    state: MeetingState = {
        "messages": [],
        "agendas": [],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "start_time": 0.0,
    }

    result = await node(state)

    # 사용자 입력이 메시지로 추가됨
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == test_input
    assert result["messages"][0].name == "TestUser"


def test_create_meeting_workflow_integration():
    """create_meeting_workflow 통합 테스트"""
    from thetable.graph.workflow import create_meeting_workflow

    # 워크플로우 생성
    workflow = create_meeting_workflow()

    # 워크플로우가 정상적으로 생성되었는지 확인
    assert workflow is not None
    assert hasattr(workflow, "invoke") or hasattr(workflow, "ainvoke")
