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


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved filesystem paths for a scaffolded project."""

    root_dir: Path
    workspace_dir: Path
    workspace_file: Path
    projects_dir: Path
    project_dir: Path
    project_file: Path
    config_dir: Path
    profiles_file: Path
    agendas_file: Path
    mcp_servers_file: Path


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

    @classmethod
    def from_dict(cls, raw: object) -> "WorkspaceConfig":
        """Parse workspace metadata loaded from YAML."""
        if not isinstance(raw, dict):
            return cls()

        current_project = raw.get("current_project")
        if current_project is not None and not isinstance(current_project, str):
            current_project = str(current_project)

        projects_dir = raw.get("projects_dir", cls.projects_dir)
        version = raw.get("version", cls.version)

        return cls(
            version=int(version),
            current_project=current_project,
            projects_dir=str(projects_dir),
        )


@dataclass(frozen=True)
class ProjectConfig:
    """Serialized contents of `.doorae/projects/<slug>/project.yaml`."""

    name: str
    slug: str
    version: int = 1
    agent_profiles_path: str = "config/agent_profiles.yaml"
    agendas_path: str = "config/agendas.yaml"
    mcp_servers_path: str = "config/mcp_servers.json"

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "name": self.name,
            "slug": self.slug,
            "agent_profiles_path": self.agent_profiles_path,
            "agendas_path": self.agendas_path,
            "mcp_servers_path": self.mcp_servers_path,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "ProjectConfig":
        """Parse project metadata loaded from YAML."""
        if not isinstance(raw, dict):
            raise TypeError("Project metadata must be a mapping.")

        name = raw.get("name")
        slug = raw.get("slug")
        version = raw.get("version", cls.version)
        agent_profiles_path = raw.get("agent_profiles_path", cls.agent_profiles_path)
        agendas_path = raw.get("agendas_path", cls.agendas_path)
        mcp_servers_path = raw.get("mcp_servers_path", cls.mcp_servers_path)

        required_values = {
            "name": name,
            "slug": slug,
            "agent_profiles_path": agent_profiles_path,
            "agendas_path": agendas_path,
            "mcp_servers_path": mcp_servers_path,
        }
        normalized_values: dict[str, str] = {}
        for field_name, value in required_values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Project metadata field '{field_name}' must be a non-empty string.")
            normalized_values[field_name] = value.strip()

        return cls(
            name=normalized_values["name"],
            slug=normalized_values["slug"],
            version=int(version),
            agent_profiles_path=normalized_values["agent_profiles_path"],
            agendas_path=normalized_values["agendas_path"],
            mcp_servers_path=normalized_values["mcp_servers_path"],
        )


@dataclass(frozen=True)
class WorkspaceInitResult:
    """Summary of a workspace initialization run."""

    paths: WorkspacePaths
    copied_env_file: bool
    already_existed: bool


@dataclass(frozen=True)
class ProjectCreateResult:
    """Summary of a project scaffold creation run."""

    paths: ProjectPaths
    config: ProjectConfig


@dataclass(frozen=True)
class ProjectRunContext:
    """Resolved project metadata and config paths for `doorae run`."""

    workspace: WorkspaceConfig
    project: ProjectConfig
    project_dir: Path
    project_file: Path
    profiles_path: Path
    agendas_path: Path
