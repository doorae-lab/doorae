"""Workflow nodes"""
from typing import Dict, Any
from langchain_core.messages import AIMessage

from thetable.graph.state import MeetingState
from thetable.agents.supervisor import SupervisorAgent
from thetable.agents.base_agent import BaseAgent
from thetable.core.profile import load_agent_profiles, AgentProfile


# Global cache for agents
_supervisor_cache = None
_agent_profiles_cache = None


def get_supervisor(state: MeetingState) -> SupervisorAgent:
    """Supervisor Agent 가져오기 (캐싱)"""
    global _supervisor_cache, _agent_profiles_cache

    if _supervisor_cache is None:
        if _agent_profiles_cache is None:
            _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

        host_profile = _agent_profiles_cache.get("Host")
        if host_profile is None:
            host_profile = AgentProfile(
                name="Host",
                role="host",
                responsibilities=["회의 진행", "발언자 선택"],
                expertise=["회의 조율"]
            )

        _supervisor_cache = SupervisorAgent(
            name="Host",
            profile=host_profile
        )

    return _supervisor_cache



_agents_cache: Dict[str, BaseAgent] = {}


def get_agent(state: MeetingState, agent_name: str) -> BaseAgent:
    """Agent 가져오기 (캐싱)"""
    global _agents_cache, _agent_profiles_cache

    if agent_name not in _agents_cache:
        if _agent_profiles_cache is None:
            _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

        profile = _agent_profiles_cache.get(agent_name)
        if profile is None:
            raise ValueError(f"Profile not found for agent: {agent_name}")

        _agents_cache[agent_name] = BaseAgent(
            name=agent_name,
            profile=profile
        )

    return _agents_cache[agent_name]


def create_agent_node(agent_name: str):
    """Agent 노드 생성 팩토리"""
    async def agent_node(state: MeetingState) -> Dict[str, Any]:
        """Agent가 발언"""
        agent = get_agent(state, agent_name)

        context = {
            "phase": state["current_phase"],
            "task": state.get("current_task", ""),
            "recent_messages": state["messages"]
        }

        response = await agent.generate_response(context)

        speaker_counts = state.get("speaker_counts", {}).copy()
        speaker_counts[agent_name] = speaker_counts.get(agent_name, 0) + 1

        return {
            "messages": [AIMessage(content=response, name=agent_name)],
            "speaker_counts": speaker_counts
        }

    return agent_node


async def supervisor_node(state: MeetingState) -> Dict[str, Any]:
    """Supervisor가 다음 발언자 선택"""
    supervisor = get_supervisor(state)

    candidates = [agent.name for agent in state["agents"] if agent.name != "Host"]

    global _agent_profiles_cache
    if _agent_profiles_cache is None:
        _agent_profiles_cache = load_agent_profiles("config/agent_profiles.yaml")

    context = {
        "current_phase": state["current_phase"],
        "recent_messages": state["messages"],
        "agent_profiles": _agent_profiles_cache,
        "candidates": candidates,
        "speaker_counts": state.get("speaker_counts", {}),
        "pending_mentions": state.get("pending_mentions", [])
    }

    decision = await supervisor.select_next_speaker(context)

    return {
        "next_speaker": decision["next_speaker"],
        "current_task": decision["task"]
    }
