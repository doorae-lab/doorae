import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
