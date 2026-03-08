"""Shared meeting engine skeleton for CLI, TUI, and server adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

from thetable.config import Settings, get_settings
from thetable.core.agenda import load_agendas
from thetable.core.profile import (
    AgentProfile,
    flatten_all_profiles,
    load_agent_profiles,
    merge_profiles_with_overrides,
)
from thetable.graph.input_provider import InputProvider
from thetable.graph.workflow import build_initial_state, create_meeting_workflow
from thetable.interfaces.event_utils import extract_node_name, extract_speaker, is_delegated


@dataclass(slots=True)
class MeetingEngineSetup:
    workflow: Any
    initial_state: dict[str, Any]
    graph_config: dict[str, int]
    top_profiles: dict[str, AgentProfile]
    all_profiles: dict[str, AgentProfile]
    human_names: list[str]
    human_name_lookup: dict[str, str]


@dataclass(slots=True)
class MeetingEngineRuntimeState:
    current_speaker: str | None = None
    current_delegated_speaker: str | None = None
    current_agenda_idx: int = 0
    agendas: list[dict[str, Any]] = field(default_factory=list)
    pending_speakers: list[str] = field(default_factory=list)
    speaker_counts: dict[str, int] = field(default_factory=dict)
    participant_statuses: dict[str, str] = field(default_factory=dict)


class MeetingEngineCallback(Protocol):
    async def on_raw_event(self, event: dict[str, Any]) -> None: ...

    async def on_speaker_changed(self, speaker: str, is_delegated: bool) -> None: ...

    async def on_token(self, content: str, speaker: str, is_delegated: bool) -> None: ...

    async def on_turn_completed(self, speaker: str, is_delegated: bool) -> None: ...

    async def on_human_turn_started(self, username: str) -> None: ...

    async def on_agenda_updated(
        self,
        agendas: list[dict[str, Any]],
        current_idx: int,
    ) -> None: ...

    async def on_meeting_ended(
        self,
        agendas: list[dict[str, Any]],
        speaker_counts: dict[str, int],
    ) -> None: ...

    async def on_pending_speakers_changed(self, pending_speakers: list[str]) -> None: ...

    async def on_participant_status_changed(self, participant_name: str, status: str) -> None: ...

    async def on_tool_call(self, name: str, status: str) -> None: ...


class MeetingEngine:
    """Shared workflow setup and event dispatch surface."""

    def __init__(
        self,
        initial_message: str,
        *,
        settings: Settings | None = None,
        profiles_path: str | Path | None = None,
        input_provider: InputProvider | None = None,
        mcp_tools: dict[str, list[object]] | None = None,
        profiles_override: dict[str, AgentProfile] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._profiles_path = str(profiles_path or self._settings.agent_profiles_path)
        self._initial_message = initial_message
        self._input_provider = input_provider
        self._mcp_tools = mcp_tools or {}
        self._profiles_override = profiles_override or {}
        self._setup: MeetingEngineSetup | None = None
        self._runtime = MeetingEngineRuntimeState()

    @property
    def setup_state(self) -> MeetingEngineSetup | None:
        return self._setup

    @property
    def runtime_state(self) -> MeetingEngineRuntimeState:
        return self._runtime

    def setup(self) -> MeetingEngineSetup:
        """Build the shared workflow context for one meeting run."""
        base_profiles = load_agent_profiles(self._profiles_path)
        top_profiles = merge_profiles_with_overrides(base_profiles, self._profiles_override)

        all_profiles = flatten_all_profiles(top_profiles)
        human_names = [name for name, profile in all_profiles.items() if profile.is_human]
        human_name_lookup = {
            name.lower(): name for name, profile in all_profiles.items() if profile.is_human
        }

        workflow = create_meeting_workflow(
            profiles_path=self._profiles_path,
            input_provider=self._input_provider,
            mcp_tools=self._mcp_tools,
            profiles_override=self._profiles_override or None,
        )

        agendas = load_agendas(str(self._settings.agendas_path))
        initial_state = build_initial_state(
            settings=self._settings,
            initial_message=self._initial_message,
            human_names=human_names,
            agendas=agendas,
        )

        participant_statuses = {name: "idle" for name in all_profiles}
        initial_state["participant_statuses"] = dict(participant_statuses)

        initial_agendas = cast(list[dict[str, Any]], initial_state.get("agendas", []))
        current_agenda_idx = cast(int, initial_state.get("current_agenda_idx", 0))
        self._runtime = MeetingEngineRuntimeState(
            current_agenda_idx=current_agenda_idx,
            agendas=list(initial_agendas),
            participant_statuses=participant_statuses,
        )

        self._setup = MeetingEngineSetup(
            workflow=workflow,
            initial_state=initial_state,
            graph_config={"recursion_limit": self._settings.recursion_limit},
            top_profiles=top_profiles,
            all_profiles=all_profiles,
            human_names=human_names,
            human_name_lookup=human_name_lookup,
        )
        return self._setup

    async def iter_events(self):
        """Yield raw LangGraph events using the shared engine setup."""
        setup_state = self._setup or self.setup()
        async for event in setup_state.workflow.astream_events(
            setup_state.initial_state,
            config=setup_state.graph_config,
            version="v2",
        ):
            yield event

    async def run(self, callback: MeetingEngineCallback) -> None:
        """Stream events and dispatch them through the callback protocol."""
        async for event in self.iter_events():
            await self._dispatch_event(event, callback)

        await callback.on_meeting_ended(
            agendas=self._runtime.agendas,
            speaker_counts=self._runtime.speaker_counts,
        )

    async def _dispatch_event(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        await callback.on_raw_event(event)
        kind = event.get("event")
        if kind == "on_chain_start":
            await self._handle_chain_start(event, callback)
            return
        if kind == "on_chat_model_start":
            await self._handle_chat_model_start(event, callback)
            return
        if kind == "on_chat_model_stream":
            await self._handle_chat_model_stream(event, callback)
            return
        if kind == "on_chat_model_end":
            await self._handle_chat_model_end(event, callback)
            return
        if kind == "on_chain_end":
            await self._handle_chain_end(event, callback)
            return
        if kind == "on_tool_start":
            tool_name = event.get("name")
            if isinstance(tool_name, str) and tool_name:
                await callback.on_tool_call(tool_name, "started")
            return
        if kind == "on_tool_end":
            tool_name = event.get("name")
            if isinstance(tool_name, str) and tool_name:
                await callback.on_tool_call(tool_name, "ended")

    async def _handle_chain_start(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        event_name = event.get("name")
        setup_state = self._setup
        if isinstance(event_name, str) and setup_state is not None:
            human_name_lookup = getattr(setup_state, "human_name_lookup", {})
            human_name = human_name_lookup.get(event_name.lower())
            if human_name is not None:
                await callback.on_human_turn_started(human_name)

        if event_name != "process_response":
            return

        input_data = event.get("data", {}).get("input", {})
        agendas = input_data.get("agendas")
        current_idx = input_data.get("current_agenda_idx", 0)

        if isinstance(agendas, list):
            self._runtime.agendas = cast(list[dict[str, Any]], agendas)
        if isinstance(current_idx, int):
            self._runtime.current_agenda_idx = current_idx

        await callback.on_agenda_updated(
            agendas=self._runtime.agendas,
            current_idx=self._runtime.current_agenda_idx,
        )

    async def _handle_chat_model_start(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        tags = cast(list[str], event.get("tags", []))
        speaker = extract_speaker(event)
        if speaker is None:
            return

        delegated = is_delegated(tags)
        if delegated:
            if speaker == self._runtime.current_delegated_speaker:
                return
            self._runtime.current_delegated_speaker = speaker
        else:
            if speaker == self._runtime.current_speaker:
                return
            self._runtime.current_speaker = speaker
            self._runtime.current_delegated_speaker = None

        await callback.on_speaker_changed(speaker, delegated)

    async def _handle_chat_model_stream(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        tags = cast(list[str], event.get("tags", []))
        if "participant" not in tags:
            return

        chunk = event.get("data", {}).get("chunk")
        content = getattr(chunk, "content", "")
        if not isinstance(content, str) or not content:
            return

        delegated = is_delegated(tags)
        speaker = extract_speaker(event)
        if speaker is None:
            speaker = (
                self._runtime.current_delegated_speaker
                if delegated
                else self._runtime.current_speaker
            )
        if speaker is None:
            return

        await callback.on_token(content, speaker, delegated)

    async def _handle_chat_model_end(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        tags = cast(list[str], event.get("tags", []))
        if "participant" not in tags:
            return

        delegated = is_delegated(tags)
        speaker = extract_speaker(event)
        if speaker is None:
            speaker = (
                self._runtime.current_delegated_speaker
                if delegated
                else self._runtime.current_speaker
            )
        if speaker is None:
            return

        if delegated:
            self._runtime.current_delegated_speaker = None
        else:
            self._runtime.current_speaker = speaker

        await callback.on_turn_completed(speaker, delegated)

    async def _handle_chain_end(
        self,
        event: dict[str, Any],
        callback: MeetingEngineCallback,
    ) -> None:
        tags = cast(list[str], event.get("tags", []))
        if extract_node_name(tags) != "process_response":
            return

        output_data = event.get("data", {}).get("output", {})
        agendas = output_data.get("agendas")
        if isinstance(agendas, list):
            self._runtime.agendas = cast(list[dict[str, Any]], agendas)

        speaker_counts = output_data.get("speaker_counts")
        if isinstance(speaker_counts, dict):
            self._runtime.speaker_counts = cast(dict[str, int], speaker_counts)

        pending_speakers = output_data.get("pending_speakers")
        if isinstance(pending_speakers, list):
            self._runtime.pending_speakers = cast(list[str], pending_speakers)

        participant_statuses = output_data.get("participant_statuses")
        if isinstance(participant_statuses, dict):
            previous_statuses = dict(self._runtime.participant_statuses)
            next_statuses = cast(dict[str, str], participant_statuses)
            self._runtime.participant_statuses = next_statuses
            for name, status in next_statuses.items():
                if previous_statuses.get(name) != status:
                    await callback.on_participant_status_changed(name, status)

        if self._runtime.pending_speakers:
            await callback.on_pending_speakers_changed(self._runtime.pending_speakers)
