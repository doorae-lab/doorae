"""create_meeting_workflow input_provider/profiles_override 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

from doorae.core.profile import AgentLLMConfig, AgentProfile
from doorae.graph.input_provider import InputProvider


def test_workflow_accepts_input_provider_and_profiles_override():
    from doorae.graph.workflow import create_meeting_workflow

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

    with patch("doorae.graph.workflow.create_main_llm", return_value=mock_model), patch(
        "doorae.graph.workflow.create_task_llm", return_value=mock_model
    ), patch("doorae.graph.workflow.load_agent_profiles", return_value=base_profiles):
        workflow = create_meeting_workflow(
            input_provider=mock_provider,
            profiles_override=override_profiles,
        )

    assert workflow is not None


def test_workflow_runtime_profile_shadows_nested_agent_name() -> None:
    from doorae.graph.workflow import create_meeting_workflow

    mock_provider = AsyncMock(spec=InputProvider)
    mock_model = MagicMock()
    captured_profiles: dict[str, AgentProfile] = {}

    base_profiles = {
        "TechLead": AgentProfile(
            name="TechLead",
            role="lead",
            responsibilities=["조율"],
            expertise=["기술"],
            agents=[
                AgentProfile(
                    name="Backend",
                    role="backend",
                    responsibilities=["백엔드 검토"],
                    expertise=["API"],
                ),
                AgentProfile(
                    name="Frontend",
                    role="frontend",
                    responsibilities=["프론트엔드 검토"],
                    expertise=["UI"],
                ),
            ],
        )
    }
    override_profiles = {
        "Backend": AgentProfile(
            name="Backend",
            role="participant",
            responsibilities=["회의 참여"],
            expertise=["일반"],
            is_human=True,
        )
    }

    def _fake_create(node_type: str, **kwargs: object) -> object:
        profile = kwargs["profile"]
        profile_name = getattr(profile, "name", "unknown")
        captured_profiles[str(profile_name)] = profile
        return MagicMock(name=f"{node_type}_{profile_name}_node")

    with patch("doorae.graph.workflow.create_main_llm", return_value=mock_model), patch(
        "doorae.graph.workflow.create_task_llm", return_value=mock_model
    ), patch("doorae.graph.workflow.load_agent_profiles", return_value=base_profiles), patch(
        "doorae.graph.workflow.NodeRegistry.create",
        side_effect=_fake_create,
    ):
        workflow = create_meeting_workflow(
            input_provider=mock_provider,
            profiles_override=override_profiles,
        )

    assert workflow is not None
    assert set(captured_profiles) == {"TechLead", "Backend"}
    assert captured_profiles["TechLead"].get_child_names() == ["Frontend"]
    assert captured_profiles["Backend"].is_human is True


def test_workflow_uses_create_agent_llm_for_ai_profiles():
    from doorae.graph.workflow import create_meeting_workflow

    mock_provider = AsyncMock(spec=InputProvider)
    mock_main_model = MagicMock(name="main_model")
    mock_task_model = MagicMock(name="task_model")
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

    with patch("doorae.graph.workflow.create_main_llm", return_value=mock_main_model), patch(
        "doorae.graph.workflow.create_task_llm", return_value=mock_task_model
    ), patch("doorae.graph.workflow.load_agent_profiles", return_value=base_profiles), patch(
        "doorae.graph.workflow.create_agent_llm",
        return_value=mock_pm_model,
    ) as mock_create_agent_llm:
        workflow = create_meeting_workflow(input_provider=mock_provider)

    assert workflow is not None
    assert mock_create_agent_llm.call_count == 1
    created_profiles = [
        call.kwargs["profile"].name for call in mock_create_agent_llm.call_args_list
    ]
    assert created_profiles == ["PM"]

    for call in mock_create_agent_llm.call_args_list:
        assert call.kwargs["streaming"] is True


def test_workflow_reuses_main_model_when_profile_llm_not_set() -> None:
    from doorae.graph.workflow import create_meeting_workflow

    mock_provider = AsyncMock(spec=InputProvider)
    mock_main_model = MagicMock(name="provided_main_model")
    mock_task_model = MagicMock(name="task_model")
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
    }

    def _capture_node_models():
        captured: dict[str, object] = {}

        def _fake_create(node_type: str, **kwargs: object) -> object:
            profile = kwargs["profile"]
            profile_name = getattr(profile, "name", "unknown")
            captured[str(profile_name)] = kwargs.get("model")
            return MagicMock(name=f"{node_type}_{profile_name}_node")

        return captured, _fake_create

    captured_models, fake_create = _capture_node_models()
    with patch("doorae.graph.workflow.create_task_llm", return_value=mock_task_model), patch(
        "doorae.graph.workflow.load_agent_profiles", return_value=base_profiles
    ), patch(
        "doorae.graph.workflow.create_agent_llm",
        return_value=mock_pm_model,
    ) as mock_create_agent_llm, patch(
        "doorae.graph.workflow.NodeRegistry.create",
        side_effect=fake_create,
    ):
        workflow = create_meeting_workflow(
            main_model=mock_main_model,
            input_provider=mock_provider,
        )

    assert workflow is not None
    assert captured_models["Host"] is mock_main_model
    assert captured_models["PM"] is mock_pm_model
    assert mock_create_agent_llm.call_count == 1
