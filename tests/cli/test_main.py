"""CLI 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from thetable.__main__ import run_meeting, main


class TestRunMeeting:
    """run_meeting 함수 테스트"""

    @pytest.mark.asyncio
    async def test_run_meeting_basic(self, monkeypatch):
        """기본 회의 실행 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        # Mock workflow
        mock_workflow = MagicMock()
        mock_result = {
            "messages": [
                HumanMessage(content="회의 시작", name="User"),
                AIMessage(content="환영합니다", name="Host"),
            ],
            "current_phase": "opening",
            "speaker_counts": {"Host": 1},
        }
        mock_workflow.ainvoke = AsyncMock(return_value=mock_result)

        with patch("thetable.__main__.create_meeting_workflow", return_value=mock_workflow):
            await run_meeting("회의 시작")

        # ainvoke가 호출되었는지 확인
        mock_workflow.ainvoke.assert_called_once()
        call_args = mock_workflow.ainvoke.call_args[0][0]
        assert "messages" in call_args
        assert call_args["current_phase"] == "opening"

    @pytest.mark.asyncio
    async def test_run_meeting_custom_profiles(self, monkeypatch):
        """커스텀 프로필 경로 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_workflow = MagicMock()
        mock_workflow.ainvoke = AsyncMock(return_value={"messages": []})

        with patch("thetable.__main__.create_meeting_workflow", return_value=mock_workflow) as mock_create:
            await run_meeting("테스트", profiles_path="custom/path.yaml")

        # create_meeting_workflow가 올바른 경로로 호출되었는지 확인
        mock_create.assert_called_once_with(profiles_path="custom/path.yaml")

    @pytest.mark.asyncio
    async def test_run_meeting_stream_mode(self, monkeypatch):
        """스트리밍 모드 테스트"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        mock_workflow = MagicMock()

        async def mock_astream(state):
            yield {"messages": [AIMessage(content="첫 메시지", name="Host")]}
            yield {"messages": [AIMessage(content="두 번째 메시지", name="PM")]}

        mock_workflow.astream = mock_astream

        with patch("thetable.__main__.create_meeting_workflow", return_value=mock_workflow):
            await run_meeting("회의 시작", stream=True)

        # 에러 없이 완료되면 성공


class TestCLI:
    """CLI 인터페이스 테스트"""

    def test_main_missing_message(self):
        """메시지 인자 누락 시 에러"""
        with patch("sys.argv", ["thetable"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_help(self):
        """--help 옵션"""
        with patch("sys.argv", ["thetable", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch("thetable.__main__.asyncio.run")
    @patch("thetable.__main__.run_meeting")
    def test_main_basic_execution(self, mock_run_meeting, mock_asyncio_run, monkeypatch):
        """기본 실행"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sys.argv", ["thetable", "회의 시작"]):
            main()

        mock_asyncio_run.assert_called_once()

    @patch("thetable.__main__.asyncio.run")
    @patch("thetable.__main__.run_meeting")
    def test_main_with_profiles(self, mock_run_meeting, mock_asyncio_run, monkeypatch):
        """--profiles 옵션"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sys.argv", ["thetable", "회의 시작", "--profiles", "custom.yaml"]):
            main()

        mock_asyncio_run.assert_called_once()

    @patch("thetable.__main__.asyncio.run")
    @patch("thetable.__main__.run_meeting")
    def test_main_with_stream(self, mock_run_meeting, mock_asyncio_run, monkeypatch):
        """--stream 옵션"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        with patch("sys.argv", ["thetable", "회의 시작", "--stream"]):
            main()

        mock_asyncio_run.assert_called_once()
