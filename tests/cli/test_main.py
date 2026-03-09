"""CLI tests for Doorae and legacy TheTable entrypoints."""

from typer.testing import CliRunner

import thetable.interfaces.cli as cli_module


runner = CliRunner()


def test_doorae_version_output() -> None:
    result = runner.invoke(cli_module.doorae_app, ["--version"])
    assert result.exit_code == 0
    assert "Doorae version: 0.1.0" in result.stdout


def test_doorae_help_shows_new_command_structure() -> None:
    result = runner.invoke(cli_module.doorae_app, ["--help"])
    assert result.exit_code == 0
    assert "Doorae" in result.stdout
    assert "run" in result.stdout
    assert "init" in result.stdout
    assert "project" in result.stdout
    assert "--message" in result.stdout


def test_thetable_help_stays_available_for_compatibility() -> None:
    result = runner.invoke(cli_module.legacy_app, ["--help"])
    assert result.exit_code == 0
    assert "TheTable" in result.stdout
    assert "run" in result.stdout


def test_root_command_delegates_to_run_impl(monkeypatch) -> None:
    calls = {}

    def fake_run_command_impl(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(cli_module, "_run_command_impl", fake_run_command_impl)

    result = runner.invoke(cli_module.doorae_app, [])
    assert result.exit_code == 0
    assert calls["message"] == cli_module.DEFAULT_MESSAGE
    assert calls["app_title"] == "Doorae"


def test_run_subcommand_delegates_to_run_impl(monkeypatch) -> None:
    calls = {}

    def fake_run_command_impl(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(cli_module, "_run_command_impl", fake_run_command_impl)

    result = runner.invoke(cli_module.doorae_app, ["run", "--message", "custom kickoff", "--no-stream"])
    assert result.exit_code == 0
    assert calls["message"] == "custom kickoff"
    assert calls["no_stream"] is True
    assert calls["app_title"] == "Doorae"


def test_project_create_help_exposes_planned_options() -> None:
    result = runner.invoke(cli_module.doorae_app, ["project", "create", "--help"])
    assert result.exit_code == 0
    assert "--template" in result.stdout
    assert "--mcp" in result.stdout
    assert "--set-current" in result.stdout


def test_init_command_is_visible_in_help() -> None:
    result = runner.invoke(cli_module.doorae_app, ["init", "--help"])
    assert result.exit_code == 0
    assert "--force" in result.stdout
