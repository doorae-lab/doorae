import pytest
from unittest.mock import AsyncMock, MagicMock
from thetable.agents.supervisor import SupervisorAgent
from thetable.core.profile import AgentProfile


@pytest.fixture
def mock_llm():
    """Mock LLM that returns orchestration decision"""
    llm = AsyncMock()
    response = MagicMock()
    response.content = '{"next_speaker": "PM", "task": "@PM 현황을 보고하세요", "reason": "status_check phase이므로"}'
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


@pytest.fixture
def supervisor_profile():
    """Supervisor profile"""
    return AgentProfile(
        name="Host",
        role="host",
        responsibilities=["회의 진행", "발언자 선택"],
        expertise=["회의 조율"]
    )


@pytest.fixture
def agent_profiles_dict():
    """Agent profiles for context"""
    return {
        "PM": AgentProfile(
            name="PM",
            role="project_manager",
            responsibilities=["프로젝트 관리"],
            expertise=["일정 계획"]
        ),
        "TechLead": AgentProfile(
            name="TechLead",
            role="tech_lead",
            responsibilities=["기술 의사결정"],
            expertise=["시스템 설계"]
        )
    }


@pytest.mark.asyncio
async def test_supervisor_select_next_speaker(
    supervisor_profile,
    agent_profiles_dict
):
    """Supervisor가 다음 발언자 선택 테스트"""
    from unittest.mock import patch
    
    # Mock the entire chain to return the JSON string directly
    with patch('thetable.agents.supervisor.ChatPromptTemplate') as mock_prompt_class:
        with patch('thetable.agents.supervisor.StrOutputParser') as mock_parser_class:
            # Setup mock chain
            mock_chain = AsyncMock()
            mock_chain.ainvoke = AsyncMock(return_value='{"next_speaker": "PM", "task": "@PM 현황을 보고하세요", "reason": "status_check phase이므로"}')
            
            # Setup mock prompt and parser to create the chain
            mock_prompt = MagicMock()
            mock_parser = MagicMock()
            mock_prompt.__or__ = MagicMock(return_value=MagicMock())
            mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)
            
            mock_prompt_class.from_messages = MagicMock(return_value=mock_prompt)
            mock_parser_class.return_value = mock_parser
            
            # Create mock LLM
            mock_llm = AsyncMock()
            
            supervisor = SupervisorAgent(
                name="Host",
                profile=supervisor_profile,
                llm=mock_llm
            )

            context = {
                "current_phase": "status_check",
                "recent_messages": [],
                "agent_profiles": agent_profiles_dict,
                "candidates": ["PM", "TechLead"]
            }

            decision = await supervisor.select_next_speaker(context)

            assert decision["next_speaker"] == "PM"
            assert "@PM" in decision["task"]
            assert "reason" in decision
