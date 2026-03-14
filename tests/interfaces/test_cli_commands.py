"""CLI subcommand tests."""

from __future__ import annotations

from typing import Any

import pytest
from typer.testing import CliRunner

from doorae.interfaces.cli import app


runner = CliRunner()


class MockResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def json(self) -> object:
        return self._payload


def test_create_command_help_shows_server_options() -> None:
    result = runner.invoke(app, ["create", "--help"])

    assert result.exit_code == 0
    assert "--server" in result.stdout
    assert "--username" in result.stdout
    assert "--message" in result.stdout


def test_join_command_help_shows_room_argument() -> None:
    result = runner.invoke(app, ["join", "--help"])

    assert result.exit_code == 0
    assert "ROOM_ID" in result.stdout
    assert "--server" in result.stdout
    assert "--username" in result.stdout


def test_create_command_routes_to_server_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run_server_command(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("doorae.interfaces.cli._run_server_command", fake_run_server_command)

    result = runner.invoke(app, ["create", "-u", "alice", "-s", "localhost:8000"])

    assert result.exit_code == 0
    assert captured["server"] == "localhost:8000"
    assert captured["username"] == "alice"
    assert captured["room_id"] is None
    assert captured["initial_message"] == "회의를 시작합니다"


def test_create_command_uses_doorae_server_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run_server_command(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setenv("DOORAE_SERVER", "localhost:9100")
    monkeypatch.setattr("doorae.interfaces.cli._run_server_command", fake_run_server_command)

    result = runner.invoke(app, ["create"])

    assert result.exit_code == 0
    assert captured["server"] == "localhost:9100"


def test_join_command_requires_server_address() -> None:
    result = runner.invoke(app, ["join", "room-123"])

    assert result.exit_code == 1
    assert "서버 주소를 지정하세요" in result.stdout
    assert "doorae join <room_id> -s localhost:8000" in result.stdout


def test_join_command_routes_room_id_to_server_tui(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run_server_command(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("doorae.interfaces.cli._run_server_command", fake_run_server_command)

    result = runner.invoke(app, ["join", "room-123", "-u", "bob", "-s", "localhost:8000"])

    assert result.exit_code == 0
    assert captured["server"] == "localhost:8000"
    assert captured["username"] == "bob"
    assert captured["room_id"] == "room-123"


def test_rooms_command_renders_table(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.base_url = kwargs["base_url"]

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, path: str) -> MockResponse:
            assert self.base_url == "http://localhost:8000"
            assert path == "/api/rooms"
            return MockResponse(
                200,
                [
                    {
                        "id": "room-123",
                        "name": "Sprint Sync",
                        "participants_count": 2,
                        "created_at": "2026-03-14T10:00:00+00:00",
                    }
                ],
            )

    monkeypatch.setattr("doorae.interfaces.cli.httpx.AsyncClient", MockAsyncClient)

    result = runner.invoke(app, ["rooms", "-s", "localhost:8000"])

    assert result.exit_code == 0
    assert "room-123" in result.stdout
    assert "Sprint Sync" in result.stdout
    assert "2026-03-14 10:00:00Z" in result.stdout


def test_rooms_command_shows_empty_state(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, path: str) -> MockResponse:
            assert path == "/api/rooms"
            return MockResponse(200, [])

    monkeypatch.setattr("doorae.interfaces.cli.httpx.AsyncClient", MockAsyncClient)

    result = runner.invoke(app, ["rooms", "-s", "localhost:8000"])

    assert result.exit_code == 0
    assert "등록된 회의방이 없습니다." in result.stdout


def test_rooms_command_fails_for_malformed_room_entries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, path: str) -> MockResponse:
            assert path == "/api/rooms"
            return MockResponse(200, [{"name": "broken"}])

    monkeypatch.setattr("doorae.interfaces.cli.httpx.AsyncClient", MockAsyncClient)

    result = runner.invoke(app, ["rooms", "-s", "localhost:8000"])

    assert result.exit_code == 1
    assert "회의방 목록 응답의 1번째 항목 형식이 올바르지 않습니다" in result.stdout
