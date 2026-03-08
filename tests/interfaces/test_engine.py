"""Tests for the shared meeting engine skeleton."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from thetable.config import Settings
from thetable.core.profile import AgentProfile
from thetable.interfaces.engine import MeetingEngine


class RecordingCallback:
    def __init__(self) -> None:
        self.raw_events: list[dict[str, object]] = []
        self.speaker_changes: list[tuple[str, bool]] = []
        self.tokens: list[tuple[str, str, bool]] = []
        self.turns: list[tuple[str, bool]] = []
        self.human_turns: list[str] = []
        self.agenda_updates: list[tuple[list[dict[str, object]], int]] = []
        self.meeting_ended: list[tuple[list[dict[str, object]], dict[str, int]]] = []
        self.pending_updates: list[list[str]] = []
        self.status_updates: list[tuple[str, str]] = []
        self.tool_calls: list[tuple[str, str]] = []

    async def on_raw_event(self, event: dict[str, object]) -> None:
        self.raw_events.append(event)

    async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None:
        self.speaker_changes.append((speaker, is_delegated))

    async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None:
        self.tokens.append((content, speaker, is_delegated))

    async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None:
        self.turns.append((speaker, is_delegated))

    async def on_human_turn_started(self, username: str) -> None:
        self.human_turns.append(username)

    async def on_agenda_updated(
        self,
        agendas: list[dict[str, object]],
        current_idx: int,
    ) -> None:
        self.agenda_updates.append((agendas, current_idx))

    async def on_meeting_ended(
        self,
        agendas: list[dict[str, object]],
        speaker_counts: dict[str, int],
    ) -> None:
        self.meeting_ended.append((agendas, speaker_counts))

    async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None:
        self.pending_updates.append(pending_speakers)

    async def on_participant_status_changed(self, participant_name: str, status: str) -> None:
        self.status_updates.append((participant_name, status))

    async def on_tool_call(self, name: str, status: str) -> None:
        self.tool_calls.append((name, status))


def _make_profile(name: str, is_human: bool = False, children: list[AgentProfile] | None = None):
    return AgentProfile(
        name=name,
        role="participant",
        responsibilities=["참여"],
        expertise=["일반"],
        is_human=is_human,
        agents=children,
    )


def test_setup_builds_shared_context_with_flattened_humans() -> None:
    top_profiles = {
        "Host": _make_profile(
            "Host",
            children=[_make_profile("Alice", is_human=True)],
        )
    }
    override_profiles = {"Bob": _make_profile("Bob", is_human=True)}
    mock_workflow = object()
    initial_state = {"agendas": [{"title": "안건", "status": "pending"}], "current_agenda_idx": 0}

    settings = Settings(
        agent_profiles_path="config/agent_profiles.yaml",
        agendas_path="config/agendas.yaml",
        recursion_limit=321,
    )

    with patch("thetable.interfaces.engine.load_agent_profiles", return_value=top_profiles), patch(
        "thetable.interfaces.engine.create_meeting_workflow",
        return_value=mock_workflow,
    ) as mock_create_workflow, patch(
        "thetable.interfaces.engine.load_agendas",
        return_value=[{"title": "안건", "status": "pending"}],
    ), patch(
        "thetable.interfaces.engine.build_initial_state",
        return_value=initial_state,
    ) as mock_build_initial_state:
        engine = MeetingEngine(
            initial_message="회의를 시작합니다",
            settings=settings,
            input_provider=MagicMock(),
            mcp_tools={"docs": []},
            profiles_override=override_profiles,
        )
        setup_state = engine.setup()

    assert setup_state.workflow is mock_workflow
    assert setup_state.graph_config == {"recursion_limit": 321}
    assert setup_state.human_names == ["Alice", "Bob"]
    assert setup_state.human_name_lookup == {"alice": "Alice", "bob": "Bob"}
    assert engine.runtime_state.participant_statuses == {"Host": "idle", "Alice": "idle", "Bob": "idle"}
    assert engine.setup_state is setup_state

    mock_create_workflow.assert_called_once()
    assert mock_create_workflow.call_args.kwargs["profiles_override"] == override_profiles
    assert mock_build_initial_state.call_args.kwargs["human_names"] == ["Alice", "Bob"]
    assert initial_state["participant_statuses"] == {"Host": "idle", "Alice": "idle", "Bob": "idle"}


def test_setup_allows_runtime_profile_to_shadow_nested_agent_name() -> None:
    top_profiles = {
        "TechLead": _make_profile(
            "TechLead",
            children=[
                _make_profile("Backend"),
                _make_profile("Frontend"),
            ],
        )
    }
    override_profiles = {"Backend": _make_profile("Backend", is_human=True)}
    mock_workflow = object()
    initial_state = {"agendas": [], "current_agenda_idx": 0}

    with patch("thetable.interfaces.engine.load_agent_profiles", return_value=top_profiles), patch(
        "thetable.interfaces.engine.create_meeting_workflow",
        return_value=mock_workflow,
    ), patch(
        "thetable.interfaces.engine.load_agendas",
        return_value=[],
    ), patch(
        "thetable.interfaces.engine.build_initial_state",
        return_value=initial_state,
    ):
        engine = MeetingEngine(
            initial_message="회의를 시작합니다",
            settings=Settings(),
            profiles_override=override_profiles,
        )
        setup_state = engine.setup()

    assert setup_state.all_profiles["Backend"].is_human is True
    assert setup_state.human_names == ["Backend"]
    assert setup_state.human_name_lookup == {"backend": "Backend"}
    assert setup_state.top_profiles["TechLead"].get_child_names() == ["Frontend"]
    assert engine.runtime_state.participant_statuses == {
        "TechLead": "idle",
        "Frontend": "idle",
        "Backend": "idle",
    }


@pytest.mark.asyncio
async def test_run_dispatches_callback_protocol_from_streamed_events() -> None:
    events = [
        {
            "event": "on_chain_start",
            "name": "process_response",
            "data": {
                "input": {
                    "agendas": [{"title": "안건 1", "status": "in_progress"}],
                    "current_agenda_idx": 0,
                }
            },
        },
        {
            "event": "on_chain_start",
            "name": "alice",
            "data": {},
        },
        {
            "event": "on_chat_model_start",
            "name": "ChatOpenAI",
            "tags": ["participant", "speaker:PM"],
        },
        {
            "event": "on_chat_model_stream",
            "tags": ["participant", "speaker:PM"],
            "data": {"chunk": SimpleNamespace(content="진행합니다")},
        },
        {"event": "on_tool_start", "name": "search_docs"},
        {"event": "on_tool_end", "name": "search_docs"},
        {
            "event": "on_chain_end",
            "tags": ["langgraph_node", "process_response"],
            "data": {
                "output": {
                    "agendas": [{"title": "안건 1", "status": "completed"}],
                    "pending_speakers": ["Host"],
                    "speaker_counts": {"PM": 1},
                    "participant_statuses": {"PM": "idle"},
                }
            },
        },
        {
            "event": "on_chat_model_end",
            "tags": ["participant", "speaker:PM"],
            "data": {},
        },
    ]

    async def _astream_events(state, config, version):
        assert state == {"messages": []}
        assert config == {"recursion_limit": 99}
        assert version == "v2"
        for event in events:
            yield event

    workflow = MagicMock()
    workflow.astream_events = _astream_events

    engine = MeetingEngine(
        initial_message="회의를 시작합니다",
        settings=Settings(recursion_limit=99),
    )
    engine._setup = SimpleNamespace(
        workflow=workflow,
        initial_state={"messages": []},
        graph_config={"recursion_limit": 99},
        human_name_lookup={"alice": "Alice"},
    )

    callback = RecordingCallback()
    await engine.run(callback)

    assert len(callback.raw_events) == len(events)
    assert callback.agenda_updates == [([{"title": "안건 1", "status": "in_progress"}], 0)]
    assert callback.human_turns == ["Alice"]
    assert callback.speaker_changes == [("PM", False)]
    assert callback.tokens == [("진행합니다", "PM", False)]
    assert callback.tool_calls == [("search_docs", "started"), ("search_docs", "ended")]
    assert callback.pending_updates == [["Host"]]
    assert callback.status_updates == [("PM", "idle")]
    assert callback.turns == [("PM", False)]
    assert callback.meeting_ended == [([{"title": "안건 1", "status": "completed"}], {"PM": 1})]
    assert engine.runtime_state.pending_speakers == ["Host"]
    assert engine.runtime_state.speaker_counts == {"PM": 1}
    assert engine.runtime_state.participant_statuses == {"PM": "idle"}
