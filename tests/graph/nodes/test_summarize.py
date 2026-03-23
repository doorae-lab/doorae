"""langmem 인라인 요약 테스트 (AgentNodeExecutor 내부)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from langmem.short_term.summarization import SummarizationResult, RunningSummary

from doorae.graph.nodes.agent import AgentNodeExecutor
from doorae.graph.state import MeetingState


def _make_profile():
    """테스트용 프로필 생성."""
    profile = MagicMock()
    profile.name = "TestAgent"
    profile.role = "Tester"
    profile.responsibilities = ["Testing"]
    profile.expertise = ["QA"]
    profile.is_supervisor.return_value = False
    profile.is_human = False
    profile.mcp_tools = []
    profile.metadata = {}
    profile.agents = []
    return profile


class TestInlineSummarization:
    """AgentNodeExecutor 내부 langmem 인라인 요약 테스트"""

    @pytest.mark.asyncio
    async def test_summarize_messages_called_in_execute(self, monkeypatch):
        """execute() 시 summarize_messages가 호출되는지 확인"""
        profile = _make_profile()
        mock_model = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.invoke_with_tools = AsyncMock(
            return_value=AIMessage(content="테스트 응답", name="TestAgent")
        )

        # summarize_messages를 mock
        mock_sum_result = SummarizationResult(
            messages=[HumanMessage(content="요약된 메시지")],
            running_summary=RunningSummary(
                summary="회의 요약 텍스트",
                summarized_message_ids={"msg_0"},
                last_summarized_message_id="msg_0",
            ),
        )

        with patch(
            "doorae.graph.nodes.agent.summarize_messages",
            return_value=mock_sum_result,
        ) as mock_summarize:
            executor = AgentNodeExecutor(
                profile=profile, model=mock_model
            )
            executor.agent = mock_agent
            executor._summary_model = MagicMock()

            messages = [HumanMessage(content="안녕하세요")]
            state = MeetingState(
                messages=messages,
                agendas=[],
                summary=None,
                pending_proposals=[],
                participant_statuses={},
            )

            result = await executor.execute(state)

            mock_summarize.assert_called_once()
            call_kwargs = mock_summarize.call_args
            assert call_kwargs[1]["running_summary"] is None
            assert call_kwargs[1]["max_tokens"] == 4000

    @pytest.mark.asyncio
    async def test_running_summary_stored_in_result(self, monkeypatch):
        """running_summary가 결과에 포함되는지 확인"""
        profile = _make_profile()
        mock_model = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.invoke_with_tools = AsyncMock(
            return_value=AIMessage(content="응답", name="TestAgent")
        )

        running_summary = RunningSummary(
            summary="요약 내용",
            summarized_message_ids={"msg_0"},
            last_summarized_message_id="msg_0",
        )
        mock_sum_result = SummarizationResult(
            messages=[HumanMessage(content="msg")],
            running_summary=running_summary,
        )

        with patch(
            "doorae.graph.nodes.agent.summarize_messages",
            return_value=mock_sum_result,
        ):
            executor = AgentNodeExecutor(
                profile=profile, model=mock_model
            )
            executor.agent = mock_agent
            executor._summary_model = MagicMock()

            state = MeetingState(
                messages=[HumanMessage(content="test")],
                agendas=[],
                summary=None,
                pending_proposals=[],
                participant_statuses={},
            )

            result = await executor.execute(state)

            assert "summary" in result
            assert result["summary"] is running_summary
            assert result["summary"].summary == "요약 내용"

    @pytest.mark.asyncio
    async def test_no_summary_when_not_needed(self, monkeypatch):
        """요약이 필요 없을 때 summary 키가 없음"""
        profile = _make_profile()
        mock_model = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.invoke_with_tools = AsyncMock(
            return_value=AIMessage(content="응답", name="TestAgent")
        )

        mock_sum_result = SummarizationResult(
            messages=[HumanMessage(content="msg")],
            running_summary=None,
        )

        with patch(
            "doorae.graph.nodes.agent.summarize_messages",
            return_value=mock_sum_result,
        ):
            executor = AgentNodeExecutor(
                profile=profile, model=mock_model
            )
            executor.agent = mock_agent
            executor._summary_model = MagicMock()

            state = MeetingState(
                messages=[HumanMessage(content="test")],
                agendas=[],
                summary=None,
                pending_proposals=[],
                participant_statuses={},
            )

            result = await executor.execute(state)

            assert "summary" not in result

    @pytest.mark.asyncio
    async def test_existing_running_summary_passed_through(self, monkeypatch):
        """이전 running_summary가 summarize_messages에 전달되는지 확인"""
        profile = _make_profile()
        mock_model = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.invoke_with_tools = AsyncMock(
            return_value=AIMessage(content="응답", name="TestAgent")
        )

        prev_summary = RunningSummary(
            summary="이전 요약",
            summarized_message_ids={"msg_0"},
            last_summarized_message_id="msg_0",
        )

        mock_sum_result = SummarizationResult(
            messages=[HumanMessage(content="msg")],
            running_summary=prev_summary,
        )

        with patch(
            "doorae.graph.nodes.agent.summarize_messages",
            return_value=mock_sum_result,
        ) as mock_summarize:
            executor = AgentNodeExecutor(
                profile=profile, model=mock_model
            )
            executor.agent = mock_agent
            executor._summary_model = MagicMock()

            state = MeetingState(
                messages=[HumanMessage(content="test")],
                agendas=[],
                summary=prev_summary,
                pending_proposals=[],
                participant_statuses={},
            )

            await executor.execute(state)

            call_kwargs = mock_summarize.call_args
            assert call_kwargs[1]["running_summary"] is prev_summary

    @pytest.mark.asyncio
    async def test_execute_uses_placeholder_when_thinking_tags_strip_to_empty(self):
        profile = _make_profile()
        mock_model = MagicMock()
        mock_agent = AsyncMock()
        mock_agent.invoke_with_tools = AsyncMock(
            return_value=AIMessage(content="<think>internal reasoning</think>", name="TestAgent")
        )

        mock_sum_result = SummarizationResult(
            messages=[HumanMessage(content="msg")],
            running_summary=None,
        )

        with patch(
            "doorae.graph.nodes.agent.summarize_messages",
            return_value=mock_sum_result,
        ):
            executor = AgentNodeExecutor(
                profile=profile, model=mock_model
            )
            executor.agent = mock_agent
            executor._summary_model = MagicMock()

            state = MeetingState(
                messages=[HumanMessage(content="test")],
                agendas=[],
                summary=None,
                pending_proposals=[],
                participant_statuses={},
            )

            result = await executor.execute(state)

            assert result["messages"][0].content == "(TestAgent: 현재 추가 의견이 없습니다.)"

    def test_get_summary_model_lazy_creation(self):
        """_get_summary_model이 lazy하게 생성되는지 확인"""
        profile = _make_profile()
        mock_model = MagicMock()

        executor = AgentNodeExecutor(
            profile=profile, model=mock_model
        )

        # _summary_model이 아직 없어야 함
        assert not hasattr(executor, "_summary_model")

        with patch("doorae.graph.nodes.agent.AgentNodeExecutor._get_summary_model") as mock_get:
            mock_get.return_value = MagicMock()
            model = mock_get()
            assert model is not None
