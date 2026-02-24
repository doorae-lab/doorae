"""create_meeting_workflow input_provider/profiles_override 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

from thetable.core.profile import AgentProfile
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
