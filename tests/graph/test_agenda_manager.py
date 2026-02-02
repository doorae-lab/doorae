"""안건 관리 모듈 테스트"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from thetable.graph.agenda_manager import extract_agenda_updates, AgendaExtractionResult


@pytest.mark.asyncio
async def test_extract_agenda_updates_basic():
    """기본 안건 추출 테스트"""
    # Mock LLM
    mock_llm = MagicMock()

    # 반환값 설정
    mock_result = AgendaExtractionResult(
        items=[
            {
                "title": "기존 안건",
                "description": "",
                "status": "pending",
                "required_speakers": []
            },
            {
                "title": "새로운 배포 이슈",
                "description": "긴급 배포 건 논의",
                "status": "pending",
                "required_speakers": ["DevOps"]
            }
        ],
        changes_summary="새 안건 추가됨"
    )

    # with_structured_output이 반환하는 structured_llm을 Mock
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # 테스트 데이터
    messages = [
        HumanMessage(content="안녕하세요", name="PM"),
        HumanMessage(content="긴급 배포 건 논의가 필요합니다", name="DevOps"),
    ]

    current_items = [
        {
            "title": "기존 안건",
            "description": "",
            "status": "pending",
            "required_speakers": []
        }
    ]

    # 실행
    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=current_items,
    )

    # 검증
    assert len(result.items) == 2
    assert result.items[0]["title"] == "기존 안건"
    assert result.items[1]["title"] == "새로운 배포 이슈"
    assert mock_llm.with_structured_output.called


@pytest.mark.asyncio
async def test_extract_agenda_updates_no_change():
    """변경사항 없을 때 기존 안건 유지"""
    # Mock LLM
    mock_llm = MagicMock()

    current_items = [
        {
            "title": "기존 안건",
            "status": "pending"
        }
    ]

    # 반환값: 동일한 안건
    mock_result = AgendaExtractionResult(
        items=current_items,
        changes_summary="변경사항 없음"
    )

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # 테스트 데이터
    messages = [
        HumanMessage(content="안녕하세요", name="PM"),
    ]

    # 실행
    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=current_items,
    )

    # 검증
    assert len(result.items) == 1
    assert result.items[0]["title"] == "기존 안건"


@pytest.mark.asyncio
async def test_extract_agenda_updates_llm_failure():
    """LLM 실패 시 기존 안건 유지"""
    # Mock LLM - 에러 발생
    mock_llm = MagicMock()

    # 1차 시도 실패
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM 에러")
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # 2차 시도도 실패
    mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM 에러"))

    current_items = [
        {
            "title": "기존 안건",
            "status": "pending"
        }
    ]

    messages = [
        HumanMessage(content="테스트", name="PM"),
    ]

    # 실행
    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=current_items,
    )

    # 검증: 기존 안건이 그대로 유지되어야 함
    assert len(result.items) == 1
    assert result.items[0]["title"] == "기존 안건"
    assert "실패" in result.changes_summary


@pytest.mark.asyncio
async def test_extract_agenda_updates_status_change():
    """안건 상태 변경 테스트"""
    # Mock LLM
    mock_llm = MagicMock()

    # 상태가 변경된 안건 반환
    mock_result = AgendaExtractionResult(
        items=[
            {
                "title": "배포 이슈",
                "status": "completed",  # pending → completed
                "decision": "내일 배포하기로 결정"
            }
        ],
        changes_summary="안건 완료 처리"
    )

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # 테스트 데이터
    messages = [
        HumanMessage(content="배포는 내일 하기로 결정했습니다", name="Host"),
    ]

    current_items = [
        {
            "title": "배포 이슈",
            "status": "pending"
        }
    ]

    # 실행
    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=current_items,
    )

    # 검증
    assert result.items[0]["status"] == "completed"
    assert result.items[0].get("decision") == "내일 배포하기로 결정"


@pytest.mark.asyncio
async def test_extract_agenda_updates_owner_assignment():
    """담당자 할당 테스트"""
    # Mock LLM
    mock_llm = MagicMock()

    # 담당자가 추가된 안건 반환
    mock_result = AgendaExtractionResult(
        items=[
            {
                "title": "성능 개선",
                "status": "pending",
                "owner": "TechLead"  # 담당자 할당
            }
        ]
    )

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_result
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # 테스트 데이터
    messages = [
        HumanMessage(content="성능 개선은 TechLead님이 맡아주세요", name="PM"),
    ]

    current_items = [
        {
            "title": "성능 개선",
            "status": "pending"
        }
    ]

    # 실행
    result = await extract_agenda_updates(
        llm=mock_llm,
        messages=messages,
        current_items=current_items,
    )

    # 검증
    assert result.items[0].get("owner") == "TechLead"
