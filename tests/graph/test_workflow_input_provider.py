"""create_meeting_workflow input_provider/profiles_override 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

from thetable.core.profile import AgentLLMConfig, AgentProfile
from thetable.graph.input_provider import InputProvider


def test_workflow_accepts_input_provider_and_profiles_override():
    from thetable.graph.workflow import create_meeting_workflow

    mock_provider = AsyncMock(spec=InputProvider)
    mock_model = MagicMock()

    base_profiles = {
        "Host": AgentProfile(
            name="Host",
            role="host",
            responsibilities=["진행"],
            expertise=["퍼실리테이션"],
            is_human=False,
        )
    }
    override_profiles = {
        "Alice": AgentProfile(
            name="Alice",
            role="participant",
            responsibilities=["참여"],
            expertise=["일반"],
            is_human=True,
        )
    }

    with patch("thetable.graph.workflow.create_main_llm", return_value=mock_model), patch(
        "thetable.graph.workflow.create_task_llm", return_value=mock_model
    ), patch("thetable.graph.workflow.load_agent_profiles", return_value=base_profiles):
        workflow = create_meeting_workflow(
            input_provider=mock_provider,
            profiles_override=override_profiles,
        )

    assert workflow is not None


def test_workflow_uses_create_agent_llm_for_ai_profiles():
    from thetable.graph.workflow import create_meeting_workflow

    mock_provider = AsyncMock(spec=InputProvider)
    mock_main_model = MagicMock(name="main_model")
    mock_task_model = MagicMock(name="task_model")
    mock_host_model = MagicMock(name="host_model")
    mock_pm_model = MagicMock(name="pm_model")

    base_profiles = {
        "Host": AgentProfile(
            name="Host",
            role="host",
            responsibilities=["진행"],
            expertise=["퍼실리테이션"],
            is_human=False,
        ),
        "PM": AgentProfile(
            name="PM",
            role="participant",
            responsibilities=["참여"],
            expertise=["일반"],
            is_human=False,
            llm=AgentLLMConfig(model="gpt-4.1-mini", temperature=0.3),
        ),
        "Alice": AgentProfile(
            name="Alice",
            role="participant",
            responsibilities=["질문"],
            expertise=["도메인"],
            is_human=True,
        ),
    }

    with patch("thetable.graph.workflow.create_main_llm", return_value=mock_main_model), patch(
        "thetable.graph.workflow.create_task_llm", return_value=mock_task_model
    ), patch("thetable.graph.workflow.load_agent_profiles", return_value=base_profiles), patch(
        "thetable.graph.workflow.create_agent_llm",
        side_effect=[mock_host_model, mock_pm_model],
    ) as mock_create_agent_llm:
        workflow = create_meeting_workflow(input_provider=mock_provider)

    assert workflow is not None
    assert mock_create_agent_llm.call_count == 2
    created_profiles = [
        call.kwargs["profile"].name for call in mock_create_agent_llm.call_args_list
    ]
    assert created_profiles == ["Host", "PM"]

    for call in mock_create_agent_llm.call_args_list:
        assert call.kwargs["streaming"] is True
