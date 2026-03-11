"""Services for creating and validating CLI workspaces."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from doorae import PROJECT_ROOT
from doorae.project.models import WorkspaceConfig, WorkspaceInitResult, WorkspacePaths


class WorkspaceError(RuntimeError):
    """Base error for workspace initialization failures."""


class WorkspaceExistsError(WorkspaceError):
    """Raised when a workspace already exists and force is not enabled."""


class MissingEnvTemplateError(WorkspaceError):
    """Raised when the packaged `.env.example` template cannot be found."""


def resolve_workspace_paths(
    base_dir: Path,
    *,
    env_template_path: Path | None = None,
) -> WorkspacePaths:
    """Resolve all workspace paths from a user working directory."""
    root_dir = base_dir.resolve()
    workspace_dir = root_dir / ".doorae"
    return WorkspacePaths(
        root_dir=root_dir,
        workspace_dir=workspace_dir,
        workspace_file=workspace_dir / "workspace.yaml",
        projects_dir=workspace_dir / "projects",
        env_file=root_dir / ".env",
        env_template=(env_template_path or PROJECT_ROOT / ".env.example").resolve(),
    )


def init_workspace(
    base_dir: Path,
    *,
    force: bool = False,
    env_template_path: Path | None = None,
) -> WorkspaceInitResult:
    """Initialize `.doorae` metadata in the provided directory."""
    paths = resolve_workspace_paths(base_dir, env_template_path=env_template_path)
    already_existed = (
        paths.workspace_dir.exists()
        or paths.workspace_file.exists()
        or paths.projects_dir.exists()
    )

    if already_existed and not force:
        raise WorkspaceExistsError(
            f"Workspace already exists at {paths.workspace_dir}. Re-run with --force to rewrite workspace metadata."
        )

    if not paths.env_file.exists() and not paths.env_template.exists():
        raise MissingEnvTemplateError(
            f"Could not find the packaged .env.example template at {paths.env_template}."
        )

    paths.workspace_dir.mkdir(parents=True, exist_ok=True)
    paths.projects_dir.mkdir(parents=True, exist_ok=True)

    workspace_text = yaml.safe_dump(
        WorkspaceConfig().to_dict(),
        allow_unicode=True,
        sort_keys=False,
    )
    paths.workspace_file.write_text(workspace_text, encoding="utf-8")

    copied_env_file = False
    if not paths.env_file.exists():
        shutil.copyfile(paths.env_template, paths.env_file)
        copied_env_file = True

    return WorkspaceInitResult(
        paths=paths,
        copied_env_file=copied_env_file,
        already_existed=already_existed,
    )
