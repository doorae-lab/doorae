"""Data models for workspace management."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspacePaths:
    """Resolved filesystem paths for a CLI workspace."""

    root_dir: Path
    workspace_dir: Path
    workspace_file: Path
    projects_dir: Path
    env_file: Path
    env_template: Path


@dataclass(frozen=True)
class WorkspaceConfig:
    """Serialized contents of `.doorae/workspace.yaml`."""

    version: int = 1
    current_project: str | None = None
    projects_dir: str = ".doorae/projects"

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "current_project": self.current_project,
            "projects_dir": self.projects_dir,
        }


@dataclass(frozen=True)
class WorkspaceInitResult:
    """Summary of a workspace initialization run."""

    paths: WorkspacePaths
    copied_env_file: bool
    already_existed: bool
