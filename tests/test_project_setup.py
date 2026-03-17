"""Project bootstrap service tests."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
import shutil

import pytest
import yaml

from doorae import PROJECT_ROOT
from doorae.project import (
    CurrentProjectNotSetError,
    ProjectExistsError,
    ProjectConfigError,
    ProjectNotFoundError,
    WorkspaceNotFoundError,
    create_project,
    init_workspace,
    resolve_project_run,
)


def read_packaged_template(relative_path: str) -> str:
    resource = resources.files("doorae.templates")
    for part in ("default", *Path(relative_path).parts):
        resource = resource / part
    return resource.read_text(encoding="utf-8")


def create_workspace_dir(name: str) -> Path:
    workspace = PROJECT_ROOT / ".tmp" / "project-tests" / name
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def remove_workspace_dir(workspace: Path) -> None:
    shutil.rmtree(workspace, ignore_errors=True)


def test_packaged_templates_are_available() -> None:
    assert "OPENAI_API_KEY" in read_packaged_template(".env.example")
    assert "agents:" in read_packaged_template("config/agent_profiles.yaml")
    assert "agendas:" in read_packaged_template("config/agendas.yaml")
    assert '"mcpServers"' in read_packaged_template("config/mcp_servers.json")


def test_create_project_scaffold_creates_expected_files() -> None:
    workspace = create_workspace_dir("scaffold")
    try:
        init_workspace(workspace)
        workspace_file = workspace / ".doorae" / "workspace.yaml"
        workspace_file.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "current_project": "keep-me",
                    "projects_dir": ".doorae/projects",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        result = create_project(workspace, "Weekly Dev")

        assert result.config.slug == "weekly-dev"
        assert result.paths.project_dir == workspace / ".doorae" / "projects" / "weekly-dev"
        assert result.paths.project_file.exists()
        assert result.paths.profiles_file.exists()
        assert result.paths.agendas_file.exists()
        assert result.paths.mcp_servers_file.exists()

        project_data = yaml.safe_load(result.paths.project_file.read_text(encoding="utf-8"))
        assert project_data == {
            "version": 1,
            "name": "Weekly Dev",
            "slug": "weekly-dev",
            "agent_profiles_path": "config/agent_profiles.yaml",
            "agendas_path": "config/agendas.yaml",
            "mcp_servers_path": "config/mcp_servers.json",
        }

        assert result.paths.profiles_file.read_text(
            encoding="utf-8"
        ) == read_packaged_template("config/agent_profiles.yaml")
        assert result.paths.agendas_file.read_text(encoding="utf-8") == read_packaged_template(
            "config/agendas.yaml"
        )
        assert result.paths.mcp_servers_file.read_text(
            encoding="utf-8"
        ) == read_packaged_template("config/mcp_servers.json")

        workspace_data = yaml.safe_load(workspace_file.read_text(encoding="utf-8"))
        assert workspace_data["current_project"] == "keep-me"
    finally:
        remove_workspace_dir(workspace)


def test_create_project_requires_initialized_workspace() -> None:
    workspace = create_workspace_dir("missing-workspace")
    try:
        with pytest.raises(WorkspaceNotFoundError, match="Run 'doorae init' first"):
            create_project(workspace, "demo")
    finally:
        remove_workspace_dir(workspace)


def test_create_project_rejects_duplicate_slug() -> None:
    workspace = create_workspace_dir("duplicate")
    try:
        init_workspace(workspace)
        create_project(workspace, "Weekly Dev")

        with pytest.raises(ProjectExistsError, match="weekly-dev"):
            create_project(workspace, "weekly_dev")
    finally:
        remove_workspace_dir(workspace)


def test_resolve_project_run_uses_current_project_from_workspace() -> None:
    workspace = create_workspace_dir("resolve-current-project")
    try:
        init_workspace(workspace)
        create_result = create_project(workspace, "Weekly Dev")

        workspace_file = workspace / ".doorae" / "workspace.yaml"
        workspace_file.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "current_project": "weekly-dev",
                    "projects_dir": ".doorae/projects",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        run_context = resolve_project_run(workspace)

        assert run_context.project.slug == "weekly-dev"
        assert run_context.project_dir == create_result.paths.project_dir
        assert run_context.project_file == create_result.paths.project_file
        assert run_context.profiles_path == create_result.paths.profiles_file
        assert run_context.agendas_path == create_result.paths.agendas_file
    finally:
        remove_workspace_dir(workspace)


def test_resolve_project_run_accepts_relative_project_path() -> None:
    workspace = create_workspace_dir("resolve-project-path")
    try:
        init_workspace(workspace)
        create_result = create_project(workspace, "Weekly Dev")

        run_context = resolve_project_run(
            workspace,
            project=".doorae/projects/weekly-dev",
        )

        assert run_context.project.slug == "weekly-dev"
        assert run_context.project_dir == create_result.paths.project_dir
        assert run_context.profiles_path == create_result.paths.profiles_file
        assert run_context.agendas_path == create_result.paths.agendas_file
    finally:
        remove_workspace_dir(workspace)


def test_resolve_project_run_requires_current_project_when_selector_missing() -> None:
    workspace = create_workspace_dir("resolve-no-current-project")
    try:
        init_workspace(workspace)
        create_project(workspace, "Weekly Dev")

        with pytest.raises(CurrentProjectNotSetError, match="current_project"):
            resolve_project_run(workspace)
    finally:
        remove_workspace_dir(workspace)


def test_resolve_project_run_rejects_unknown_project_slug() -> None:
    workspace = create_workspace_dir("resolve-missing-project")
    try:
        init_workspace(workspace)

        with pytest.raises(ProjectNotFoundError, match="missing-project"):
            resolve_project_run(workspace, project="missing-project")
    finally:
        remove_workspace_dir(workspace)


def test_resolve_project_run_rejects_invalid_project_config_paths() -> None:
    workspace = create_workspace_dir("resolve-invalid-project-config")
    try:
        init_workspace(workspace)
        create_result = create_project(workspace, "Weekly Dev")
        create_result.paths.project_file.write_text(
            yaml.safe_dump(
                {
                    "version": 1,
                    "name": "Weekly Dev",
                    "slug": "weekly-dev",
                    "agent_profiles_path": "config/missing-profiles.yaml",
                    "agendas_path": "config/agendas.yaml",
                    "mcp_servers_path": "config/mcp_servers.json",
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        with pytest.raises(ProjectConfigError, match="agent_profiles_path"):
            resolve_project_run(workspace, project="weekly-dev")
    finally:
        remove_workspace_dir(workspace)
