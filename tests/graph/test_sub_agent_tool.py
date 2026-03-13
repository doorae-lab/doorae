from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from doorae.core.profile import AgentProfile
from doorae.graph.sub_agent_tool import create_sub_agent_tool


WEEKDAYS = {
    0: "월요일",
    1: "화요일",
    2: "수요일",
    3: "목요일",
    4: "금요일",
    5: "토요일",
    6: "일요일",
}


def _expected_today_context() -> str:
    now = datetime.now()
    return f"오늘은 {now.year}년 {now.month}월 {now.day}일 ({WEEKDAYS[now.weekday()]})입니다."


def test_create_sub_agent_tool_name_and_description():
    sub_profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계", "DB 최적화"],
        expertise=["Python", "PostgreSQL"],
    )

    tool = create_sub_agent_tool(
        sub_profile=sub_profile,
        model=MagicMock(),
        parent_name="TechLead",
        mcp_tools={},
    )

    assert tool.name == "ask_backend"
    assert "상위 에이전트: TechLead" in tool.description
    assert "책임: API 설계, DB 최적화" in tool.description
    assert "전문분야: Python, PostgreSQL" in tool.description


@pytest.mark.asyncio
async def test_sub_agent_tool_includes_today_context_in_system_message():
    sub_profile = AgentProfile(
        name="Backend",
        role="backend_engineer",
        responsibilities=["API 설계"],
        expertise=["Python"],
    )
    invoke_with_tools_mock = AsyncMock(return_value=MagicMock(content="응답"))

    with patch(
        "doorae.graph.sub_agent_tool.BaseAgent.invoke_with_tools",
        new=invoke_with_tools_mock,
    ):
        tool = create_sub_agent_tool(
            sub_profile=sub_profile,
            model=MagicMock(),
            parent_name="TechLead",
            mcp_tools={},
        )

        await tool.ainvoke({"question": "현재 상태 알려줘"})

    call_args = invoke_with_tools_mock.await_args
    assert call_args is not None
    messages = call_args.args[0]
    assert _expected_today_context() in messages[0].content
