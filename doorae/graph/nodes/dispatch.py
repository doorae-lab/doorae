"""Dispatch node that delegates a turn to the current participant executor."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage

from doorae.config import get_settings
from doorae.core.profile import AgentProfile
from doorae.graph.nodes.agent import AgentNodeExecutor
from doorae.graph.nodes.base import BaseNode, NodeType
from doorae.graph.nodes.human import HumanNodeExecutor
from doorae.graph.nodes.registry import register_node
from doorae.graph.participant_registry import ParticipantRegistry
from doorae.graph.state import MeetingState


@register_node("dispatch", category="dispatch")
class DispatchNode(BaseNode):
    """Single participant node that looks up the active speaker at runtime."""

    node_type = NodeType.DISPATCH
    requires_llm = True
    requires_tools = True

    def __init__(
        self,
        registry: ParticipantRegistry,
        input_provider=None,
        agent_models: dict[str, Any] | None = None,
        mcp_tools: dict[str, list] | None = None,
        settings=None,
        **kwargs,
    ) -> None:
        self._registry = registry
        self._human_executor = HumanNodeExecutor(input_provider=input_provider)
        self._agent_models = agent_models or {}
        self._mcp_tools = mcp_tools or {}
        self._settings = settings or get_settings()
        self._agent_executors: dict[str, AgentNodeExecutor] = {}

    def _get_agent_executor(self, profile: AgentProfile) -> AgentNodeExecutor:
        executor = self._agent_executors.get(profile.name)
        if executor is None:
            executor = AgentNodeExecutor(
                profile=profile,
                model=self._agent_models.get(profile.name),
                mcp_tools=self._mcp_tools,
                settings=self._settings,
            )
            self._agent_executors[profile.name] = executor
        return executor

    def _current_profiles(self) -> dict[str, AgentProfile]:
        profiles: dict[str, AgentProfile] = {}
        for name in self._registry.all_names:
            profile = self._registry.get(name)
            if profile is not None:
                profiles[name] = profile
        return profiles

    async def execute(self, state: MeetingState) -> dict[str, Any]:
        pending = list(state.get("pending_speakers", []))
        if not pending:
            return {}

        speaker = pending[0]
        profile = self._registry.get(speaker)
        if profile is None:
            return {
                "pending_speakers": pending[1:],
                "messages": [SystemMessage(content=f"{speaker}님이 퇴장했습니다.")],
            }

        if profile.is_human:
            return await self._human_executor.execute(state, profile)

        all_names = self._registry.all_names
        all_profiles = self._current_profiles()
        executor = self._get_agent_executor(profile)
        return await executor.execute(
            state,
            all_agent_names=all_names,
            all_profiles=all_profiles,
        )
