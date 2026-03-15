"""DispatchNode tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from doorae.core.profile import AgentProfile
from doorae.graph.nodes.dispatch import DispatchNode
from doorae.graph.participant_registry import ParticipantRegistry


def _make_profile(name: str, *, is_human: bool = False, role: str = "participant") -> AgentProfile:
    return AgentProfile(
        name=name,
        role=role,
        responsibilities=["참여"],
        expertise=["일반"],
        is_human=is_human,
    )


def _make_state(pending_speakers: list[str]) -> dict:
    return {
        "messages": [],
        "agendas": [{"title": "안건", "status": "in_progress"}],
        "current_agenda_idx": 0,
        "pending_speakers": pending_speakers,
        "speaker_counts": {},
        "participant_statuses": {},
        "turn_count": 0,
        "max_turns": 1000,
    }


@pytest.mark.asyncio
async def test_dispatch_delegates_to_human_executor() -> None:
    registry = ParticipantRegistry({"Alice": _make_profile("Alice", is_human=True)})
    node = DispatchNode(registry=registry, input_provider=MagicMock())
    node._human_executor.execute = AsyncMock(
        return_value={"messages": [HumanMessage(content="안녕하세요", name="Alice")]}
    )

    result = await node.execute(_make_state(["Alice"]))

    node._human_executor.execute.assert_awaited_once()
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].name == "Alice"


@pytest.mark.asyncio
async def test_dispatch_delegates_to_agent_executor_with_dynamic_names() -> None:
    registry = ParticipantRegistry(
        {
            "Host": _make_profile("Host", role="host"),
            "Alice": _make_profile("Alice", is_human=True),
        }
    )
    node = DispatchNode(registry=registry, agent_models={"Host": MagicMock()})
    fake_executor = MagicMock()
    fake_executor.execute = AsyncMock(
        return_value={"messages": [AIMessage(content="진행하겠습니다", name="Host")]}
    )
    node._get_agent_executor = MagicMock(return_value=fake_executor)

    result = await node.execute(_make_state(["Host"]))

    node._get_agent_executor.assert_called_once()
    fake_executor.execute.assert_awaited_once()
    call_kwargs = fake_executor.execute.await_args.kwargs
    assert call_kwargs["all_agent_names"] == ["Host", "Alice"]
    assert set(call_kwargs["all_profiles"]) == {"Host", "Alice"}
    assert isinstance(result["messages"][0], AIMessage)


@pytest.mark.asyncio
async def test_dispatch_skips_missing_participant() -> None:
    node = DispatchNode(registry=ParticipantRegistry())

    result = await node.execute(_make_state(["Alice", "Host"]))

    assert result["pending_speakers"] == ["Host"]
    assert isinstance(result["messages"][0], SystemMessage)
    assert result["messages"][0].content == "Alice님이 퇴장했습니다."
