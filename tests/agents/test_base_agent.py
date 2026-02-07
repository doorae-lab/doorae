import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from langchain_core.messages import AIMessage
from thetable.agents.base_agent import BaseAgent
from thetable.core.profile import AgentProfile


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
    with patch('thetable.agents.base_agent.ChatPromptTemplate') as mock_prompt_class:
        with patch('thetable.agents.base_agent.StrOutputParser') as mock_parser_class:
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


@pytest.mark.asyncio
async def test_ainvoke_with_retry_success_on_first_attempt(agent_profile):
    """첫 시도에서 성공하는 경우"""
    mock_llm = AsyncMock()
    mock_response = AIMessage(content="성공")
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm
    )

    result = await agent._ainvoke_with_retry(mock_llm, [], config=None)

    assert result == mock_response
    assert mock_llm.ainvoke.call_count == 1


@pytest.mark.asyncio
async def test_ainvoke_with_retry_success_after_transient_error(agent_profile):
    """일시적 네트워크 오류 후 재시도 성공"""
    mock_llm = AsyncMock()
    mock_response = AIMessage(content="성공")

    # 첫 번째 호출: RemoteProtocolError, 두 번째 호출: 성공
    mock_llm.ainvoke = AsyncMock(
        side_effect=[
            httpx.RemoteProtocolError("peer closed connection"),
            mock_response
        ]
    )

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm
    )

    # asyncio.sleep을 mock하여 테스트 속도 향상
    with patch('asyncio.sleep', new_callable=AsyncMock):
        result = await agent._ainvoke_with_retry(mock_llm, [], config=None, max_retries=3)

    assert result == mock_response
    assert mock_llm.ainvoke.call_count == 2


@pytest.mark.asyncio
async def test_ainvoke_with_retry_max_retries_exceeded(agent_profile):
    """최대 재시도 횟수 초과 시 예외 전파"""
    mock_llm = AsyncMock()

    # 모든 시도에서 네트워크 오류 발생
    mock_llm.ainvoke = AsyncMock(
        side_effect=httpx.RemoteProtocolError("peer closed connection")
    )

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm
    )

    with patch('asyncio.sleep', new_callable=AsyncMock):
        with pytest.raises(httpx.RemoteProtocolError, match="peer closed connection"):
            await agent._ainvoke_with_retry(mock_llm, [], config=None, max_retries=3)

    assert mock_llm.ainvoke.call_count == 3


@pytest.mark.asyncio
async def test_ainvoke_with_retry_non_retryable_exception(agent_profile):
    """재시도 대상이 아닌 예외는 즉시 전파"""
    mock_llm = AsyncMock()

    # ValueError는 재시도 대상 예외가 아님
    mock_llm.ainvoke = AsyncMock(
        side_effect=ValueError("Invalid input")
    )

    agent = BaseAgent(
        name="TestAgent",
        profile=agent_profile,
        llm=mock_llm
    )

    with pytest.raises(ValueError, match="Invalid input"):
        await agent._ainvoke_with_retry(mock_llm, [], config=None, max_retries=3)

    # 재시도하지 않고 즉시 실패
    assert mock_llm.ainvoke.call_count == 1
