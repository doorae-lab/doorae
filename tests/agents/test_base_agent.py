from datetime import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from doorae.agents.base_agent import BaseAgent
from doorae.core.profile import AgentProfile


WEEKDAYS = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def _expected_today_context() -> str:
    now = datetime.now()
    return f"Today is {now.year:04d}-{now.month:02d}-{now.day:02d} ({WEEKDAYS[now.weekday()]})."


@pytest.fixture
def mock_llm():
    """Mock LLM"""
    llm = AsyncMock()
    # Mock the ainvoke method to return a string directly for the StrOutputParser
    # The chain will be: prompt | llm | StrOutputParser
    # After the LLM, the output parser expects the content to be extracted
    mock_response = MagicMock()
    mock_response.content = "Test response"
    llm.ainvoke = AsyncMock(return_value=mock_response)
    return llm


@pytest.fixture
def agent_profile():
    """Test agent profile"""
    return AgentProfile(
        name="TestAgent",
        role="tester",
        responsibilities=["테스트 수행"],
        expertise=["테스트 자동화"]
    )


@pytest.mark.asyncio
async def test_base_agent_generate_response(agent_profile):
    """BaseAgent 응답 생성 테스트"""
    # Mock the entire chain execution
    with patch('doorae.agents.base_agent.ChatPromptTemplate') as mock_prompt_class:
        with patch('doorae.agents.base_agent.StrOutputParser') as mock_parser_class:
            # Setup mock chain
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value="Test response")

            # Setup mock prompt and parser to create the chain
            mock_prompt = MagicMock()
            mock_parser = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=MagicMock())
            mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

            mock_prompt_class.from_messages = MagicMock(return_value=mock_prompt)
            mock_parser_class.return_value = mock_parser

            # Create mock LLM
            mock_llm = AsyncMock()

            agent = BaseAgent(
                name="TestAgent",
                profile=agent_profile,
                llm=mock_llm
            )

            context = {
                "phase": "status_check",
                "task": "현황을 보고하세요",
                "recent_messages": []
            }

            response = await agent.generate_response(context)

            assert response == "Test response"
            assert mock_chain.ainvoke.called


def test_base_agent_system_prompt_includes_today_context(agent_profile):
    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=MagicMock(),
    )

    assert _expected_today_context() in agent._system_prompt


@pytest.mark.asyncio
async def test_invoke_with_tools_unknown_tool_returns_error_message(agent_profile):
    bound_llm = AsyncMock()
    bound_llm.ainvoke = AsyncMock(
        side_effect=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "missing_tool",
                        "args": {"query": "open issues"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Recovered response"),
        ]
    )

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = bound_llm

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm,
    )

    class DummyTool:
        name = "existing_tool"

        async def ainvoke(self, _args):
            return "unused"

    response = await agent.invoke_with_tools(
        [HumanMessage(content="Check the current issues")],
        extra_tools=[DummyTool()],
    )

    assert response.content == "Recovered response"
    assert bound_llm.ainvoke.await_count == 2

    second_call_messages = bound_llm.ainvoke.await_args_list[1].args[0]
    tool_messages = [msg for msg in second_call_messages if isinstance(msg, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].tool_call_id == "call-1"
    assert "missing_tool" in tool_messages[0].content
    assert "existing_tool" in tool_messages[0].content


@pytest.mark.asyncio
async def test_invoke_with_tools_strips_thinking_tags_without_tools(agent_profile):
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="<think>reasoning</think>actual response")
    )

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm,
    )

    response = await agent.invoke_with_tools([HumanMessage(content="Respond")])

    assert response.content == "actual response"


@pytest.mark.asyncio
async def test_invoke_with_tools_strips_thinking_tags_after_tool_loop(agent_profile):
    bound_llm = AsyncMock()
    bound_llm.ainvoke = AsyncMock(
        return_value=AIMessage(content="<think>reasoning</think>")
    )

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = bound_llm

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm,
    )

    class DummyTool:
        name = "existing_tool"

        async def ainvoke(self, _args):
            return "unused"

    response = await agent.invoke_with_tools(
        [HumanMessage(content="Respond")],
        extra_tools=[DummyTool()],
    )

    assert response.content == ""
