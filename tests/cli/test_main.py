"""CLI tests for Doorae."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from doorae import PROJECT_ROOT
from doorae.config import Settings
from doorae.interfaces.cli import (
    _normalize_server_base_urls,
    _setup_server_room,
    app,
    run_meeting,
)
from doorae.project import WorkspaceError, init_workspace


runner = CliRunner()


def create_workspace_dir(name: str) -> Path:
    """Create a writable workspace directory inside the repository sandbox."""
    workspace = PROJECT_ROOT / ".tmp" / "cli-tests" / name
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def remove_workspace_dir(workspace: Path) -> None:
    shutil.rmtree(workspace, ignore_errors=True)


def build_subprocess_env() -> dict[str, str]:
    """Run subprocess smoke tests against the current worktree, not an installed wheel."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(PROJECT_ROOT) if not existing else f"{PROJECT_ROOT}{os.pathsep}{existing}"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def test_cli_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Doorae" in result.stdout
    assert "init" in result.stdout
    assert "--message" in result.stdout
    assert "--server" in result.stdout
    assert "--room" in result.stdout
    assert "--username" in result.stdout


def test_cli_default_message() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--message" in result.stdout


def test_cli_custom_message() -> None:
    result = runner.invoke(app, ["--message", "커스텀 회의", "--help"])
    assert result.exit_code == 0


def test_cli_no_stream_option() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--no-stream" in result.stdout


def test_normalize_server_base_urls_supports_ws_scheme() -> None:
    ws_base, http_base = _normalize_server_base_urls("ws://localhost:8000/")

    assert ws_base == "ws://localhost:8000"
    assert http_base == "http://localhost:8000"


def test_normalize_server_base_urls_supports_http_scheme() -> None:
    ws_base, http_base = _normalize_server_base_urls("https://example.com/doorae/")

    assert ws_base == "wss://example.com/doorae"
    assert http_base == "https://example.com/doorae"


class MockResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
async def test_setup_server_room_creates_room_and_builds_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.base_url = kwargs["base_url"]
            self.timeout = kwargs["timeout"]

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def post(self, path: str, json: dict[str, Any]) -> MockResponse:
            assert path == "/api/rooms"
            assert json == {"name": "Doorae Room (alice user)"}
            return MockResponse(201, {"id": "room-123"})

    monkeypatch.setattr("doorae.interfaces.cli.httpx.AsyncClient", MockAsyncClient)

    session = await _setup_server_room("ws://localhost:8000/", None, "alice user")

    assert session.room_id == "room-123"
    assert session.ws_url == "ws://localhost:8000/ws/room-123?username=alice%20user"
    assert session.start_url == "http://localhost:8000/api/rooms/room-123/start"


@pytest.mark.asyncio
async def test_setup_server_room_errors_for_missing_room(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.base_url = kwargs["base_url"]
            self.timeout = kwargs["timeout"]

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, path: str) -> MockResponse:
            assert path == "/api/rooms/missing-room"
            return MockResponse(404, {"detail": "회의방을 찾을 수 없습니다."})

    monkeypatch.setattr("doorae.interfaces.cli.httpx.AsyncClient", MockAsyncClient)

    with pytest.raises(RuntimeError, match="회의방을 찾을 수 없습니다: missing-room"):
        await _setup_server_room("http://localhost:8000", "missing-room", "alice")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested_room_id", "show_server_invite"),
    [
        (None, True),
        ("existing-room", False),
    ],
)
async def test_run_meeting_passes_server_room_metadata_to_tui(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    requested_room_id: str | None,
    show_server_invite: bool,
) -> None:
    captured_kwargs: dict[str, Any] = {}

    class StubMeetingTuiApp:
        def __init__(self, **kwargs: Any) -> None:
            captured_kwargs.update(kwargs)

        async def run_async(self) -> None:
            return

    async def stub_setup_server_room(
        server_url: str,
        room_id: str | None,
        username: str,
    ) -> Any:
        assert server_url == "ws://localhost:8000"
        assert room_id == requested_room_id
        assert username == "alice"
        return type(
            "ServerSession",
            (),
            {
                "room_id": "room-123",
                "ws_url": "ws://localhost:8000/ws/room-123?username=alice",
                "start_url": "http://localhost:8000/api/rooms/room-123/start",
            },
        )()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("doorae.interfaces.cli._setup_server_room", stub_setup_server_room)
    monkeypatch.setattr("doorae.interfaces.tui.MeetingTuiApp", StubMeetingTuiApp)

    await run_meeting(
        initial_message="hello",
        settings=Settings(),
        use_tui=True,
        server_url="ws://localhost:8000",
        room_id=requested_room_id,
        username="alice",
    )

    assert captured_kwargs["room_id"] == "room-123"
    assert captured_kwargs["show_server_invite"] is show_server_invite


def test_init_command_is_visible_in_help() -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout


def test_python_module_help_stays_side_effect_free() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "doorae", "--help"],
        cwd=PROJECT_ROOT,
        env=build_subprocess_env(),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    combined_output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "init" in result.stdout
    assert "| DEBUG    |" not in combined_output
    assert "노드 등록" not in combined_output


def test_module_init_command_creates_workspace() -> None:
    workspace = create_workspace_dir("module-init")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "doorae", "init"],
            cwd=workspace,
            env=build_subprocess_env(),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        assert result.returncode == 0
        assert "Initialized Doorae workspace." in result.stdout
        assert (workspace / ".doorae" / "workspace.yaml").exists()
        assert (workspace / ".doorae" / "projects").is_dir()
        assert (workspace / ".env").exists()
    finally:
        remove_workspace_dir(workspace)


def test_init_creates_workspace_and_copies_env_when_missing() -> None:
    workspace = create_workspace_dir("create")
    try:
        result = init_workspace(workspace)

        workspace_file = workspace / ".doorae" / "workspace.yaml"
        assert workspace_file.exists()
        assert (workspace / ".doorae" / "projects").is_dir()
        assert (workspace / ".env").exists()
        assert result.copied_env_file is True
        assert result.already_existed is False

        workspace_data = yaml.safe_load(workspace_file.read_text(encoding="utf-8"))
        assert workspace_data == {
            "version": 1,
            "current_project": None,
            "projects_dir": ".doorae/projects",
        }
        assert (workspace / ".env").read_text(encoding="utf-8") == (
            PROJECT_ROOT / ".env.example"
        ).read_text(encoding="utf-8")
    finally:
        remove_workspace_dir(workspace)


def test_init_fails_without_force_when_workspace_exists() -> None:
    workspace = create_workspace_dir("exists")
    try:
        workspace_dir = workspace / ".doorae"
        workspace_dir.mkdir()
        (workspace_dir / "workspace.yaml").write_text("version: 99\n", encoding="utf-8")

        with pytest.raises(WorkspaceError) as exc_info:
            init_workspace(workspace)

        assert "--force" in str(exc_info.value)
    finally:
        remove_workspace_dir(workspace)


def test_init_preserves_existing_env_file() -> None:
    workspace = create_workspace_dir("env")
    try:
        (workspace / ".env").write_text("OPENAI_API_KEY=keep-me\n", encoding="utf-8")

        result = init_workspace(workspace)
        assert result.copied_env_file is False
        assert (workspace / ".env").read_text(encoding="utf-8") == "OPENAI_API_KEY=keep-me\n"
    finally:
        remove_workspace_dir(workspace)


def test_init_force_rewrites_workspace_file() -> None:
    workspace = create_workspace_dir("force")
    try:
        workspace_dir = workspace / ".doorae"
        projects_dir = workspace_dir / "projects"
        projects_dir.mkdir(parents=True)
        (workspace_dir / "workspace.yaml").write_text(
            "version: 9\ncurrent_project: legacy\nprojects_dir: legacy\n",
            encoding="utf-8",
        )

        result = init_workspace(workspace, force=True)
        assert result.already_existed is True

        workspace_data = yaml.safe_load(
            (workspace_dir / "workspace.yaml").read_text(encoding="utf-8")
        )
        assert workspace_data["version"] == 1
        assert workspace_data["current_project"] is None
        assert workspace_data["projects_dir"] == ".doorae/projects"
    finally:
        remove_workspace_dir(workspace)
