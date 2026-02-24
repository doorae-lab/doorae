"""HumanNode 리팩터링 테스트."""

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import HumanMessage

from thetable.core.profile import AgentProfile


def _make_profile(name="TestUser"):
    return AgentProfile(
        name=name,
        role="참여자",
        responsibilities=["참여"],
        expertise=["일반"],
        is_human=True,
    )


def _make_state():
    return {
        "messages": [],
        "agendas": [],
        "current_agenda_idx": 0,
        "pending_speakers": [],
        "speaker_counts": {},
        "consecutive_host_delegations": 0,
        "turn_count": 0,
        "max_turns": 1000,
        "meeting_ended": False,
        "summary": "",
        "start_time": 0.0,
    }


class TestHumanNodeWithInputProvider:
    @pytest.mark.asyncio
    async def test_execute_with_user_input(self):
        from thetable.graph.nodes.human import HumanNode

        mock_provider = AsyncMock()
        mock_provider.get_input.return_value = "안녕하세요"

        node = HumanNode(profile=_make_profile(), input_provider=mock_provider)
        result = await node.execute(_make_state())

        msg = result["messages"][0]
        assert isinstance(msg, HumanMessage)
        assert msg.content == "안녕하세요"
        assert msg.name == "TestUser"

    @pytest.mark.asyncio
    async def test_execute_with_empty_input_skips(self):
        from thetable.graph.nodes.human import HumanNode

        mock_provider = AsyncMock()
        mock_provider.get_input.return_value = ""

        node = HumanNode(profile=_make_profile(), input_provider=mock_provider)
        result = await node.execute(_make_state())
        assert result["messages"][0].content == "(발언 없음)"

    @pytest.mark.asyncio
    async def test_execute_without_provider_raises(self):
        from thetable.graph.nodes.human import HumanNode

        node = HumanNode(profile=_make_profile())
        with pytest.raises(RuntimeError, match="InputProvider가 설정되지 않았습니다"):
            await node.execute(_make_state())
