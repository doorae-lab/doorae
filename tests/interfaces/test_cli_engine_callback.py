"""Tests for CLI MeetingEngine adapter glue."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from thetable.interfaces.cli import CliMeetingCallback, _run_streaming


@pytest.mark.asyncio
async def test_run_streaming_builds_cli_callback_from_engine_state() -> None:
    engine = MagicMock()
    engine.setup_state = SimpleNamespace(initial_state={"start_time": 100.0})
    engine.run = AsyncMock()

    await _run_streaming(engine, hide_delegated=True)

    engine.run.assert_awaited_once()
    callback = engine.run.await_args.args[0]
    assert isinstance(callback, CliMeetingCallback)
    assert callback._start_time == 100.0
    assert callback._hide_delegated is True


@pytest.mark.asyncio
async def test_cli_callback_prints_pending_speakers(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[str] = []
    monkeypatch.setattr(
        "thetable.interfaces.cli.console.print",
        lambda message="", *args, **kwargs: printed.append(str(message)),
    )
    callback = CliMeetingCallback(start_time=100.0)

    await callback.on_pending_speakers_changed(["Host", "PM"])

    assert printed == ["[dim]다음 발언 예정: Host, PM[/dim]"]
