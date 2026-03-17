"""Services for creating and validating CLI workspaces and project scaffolds."""

from __future__ import annotations

import re
import unicodedata
from importlib import resources
from pathlib import Path

import yaml

from doorae.project.models import (
    ProjectConfig,
    ProjectCreateResult,
    ProjectPaths,
    ProjectRunContext,
    WorkspaceConfig,
    WorkspaceInitResult,
    WorkspacePaths,
)

TEMPLATE_PACKAGE = "doorae.templates"
ENV_TEMPLATE = Path("default/.env.example")
PROJECT_TEMPLATE_FILES = {
    Path("config/agent_profiles.yaml"): Path("default/config/agent_profiles.yaml"),
    Path("config/agendas.yaml"): Path("default/config/agendas.yaml"),
    Path("config/mcp_servers.json"): Path("default/config/mcp_servers.json"),
}


class WorkspaceError(RuntimeError):
    """Base error for workspace initialization and project scaffolding failures."""


class WorkspaceExistsError(WorkspaceError):
    """Raised when a workspace already exists and force is not enabled."""


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when project scaffolding is attempted outside an initialized workspace."""


class MissingTemplateError(WorkspaceError):
    """Raised when a packaged scaffold template cannot be found."""


class InvalidProjectNameError(WorkspaceError):
    """Raised when the provided project name cannot produce a safe slug."""


class ProjectExistsError(WorkspaceError):
    """Raised when a scaffold with the target slug already exists."""


class CurrentProjectNotSetError(WorkspaceError):
    """Raised when a workspace has no current project configured."""


class ProjectNotFoundError(WorkspaceError):
    """Raised when the requested project slug or path cannot be resolved."""


class ProjectConfigError(WorkspaceError):
    """Raised when project metadata or referenced config paths are invalid."""


def resolve_workspace_paths(base_dir: Path) -> WorkspacePaths:
    """Resolve all workspace paths from a user working directory."""
    root_dir = base_dir.resolve()
    workspace_dir = root_dir / ".doorae"
    return WorkspacePaths(
        root_dir=root_dir,
        workspace_dir=workspace_dir,
        workspace_file=workspace_dir / "workspace.yaml",
        projects_dir=workspace_dir / "projects",
        env_file=root_dir / ".env",
    )


def slugify_project_name(name: str) -> str:
    """Convert a project name into a deterministic filesystem-safe slug."""
    normalized = unicodedata.normalize("NFKC", name).strip().lower()
    normalized = normalized.replace("_", "-")
    normalized = re.sub(r"\s+", "-", normalized)
    slug = re.sub(r"[^\w-]", "-", normalized)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug:
        raise InvalidProjectNameError(
            "Project name must contain at least one letter or number after normalization."
        )
    return slug


def init_workspace(
    base_dir: Path,
    *,
    force: bool = False,
) -> WorkspaceInitResult:
    """Initialize `.doorae` metadata in the provided directory."""
    paths = resolve_workspace_paths(base_dir)
    already_existed = (
        paths.workspace_dir.exists()
        or paths.workspace_file.exists()
        or paths.projects_dir.exists()
    )

    if already_existed and not force:
        raise WorkspaceExistsError(
            f"Workspace already exists at {paths.workspace_dir}. Re-run with --force to rewrite workspace metadata."
        )

    env_template_text = _read_template_text(ENV_TEMPLATE)

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
        paths.env_file.write_text(env_template_text, encoding="utf-8")
        copied_env_file = True

    return WorkspaceInitResult(
        paths=paths,
        copied_env_file=copied_env_file,
        already_existed=already_existed,
    )


def create_project(base_dir: Path, name: str) -> ProjectCreateResult:
    """Create a scaffolded project inside the current workspace."""
    workspace_paths = resolve_workspace_paths(base_dir)
    workspace_config = _load_workspace_config(workspace_paths)
    slug = slugify_project_name(name)
    project_paths = _resolve_project_paths(workspace_paths, workspace_config, slug)

    if project_paths.project_dir.exists():
        raise ProjectExistsError(
            f"Project '{slug}' already exists at {project_paths.project_dir}."
        )

    template_text_by_destination = {
        destination: _read_template_text(template_path)
        for destination, template_path in PROJECT_TEMPLATE_FILES.items()
    }

    project_config = ProjectConfig(name=name.strip(), slug=slug)
    project_text = yaml.safe_dump(
        project_config.to_dict(),
        allow_unicode=True,
        sort_keys=False,
    )

    project_paths.project_dir.mkdir(parents=True, exist_ok=False)
    project_paths.config_dir.mkdir(parents=True, exist_ok=True)
    project_paths.project_file.write_text(project_text, encoding="utf-8")

    for destination, text in template_text_by_destination.items():
        target = project_paths.project_dir / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    return ProjectCreateResult(paths=project_paths, config=project_config)


def resolve_project_run(
    base_dir: Path,
    *,
    project: str | None = None,
) -> ProjectRunContext:
    """Resolve the project metadata and config files for `doorae run`."""
    workspace_paths = resolve_workspace_paths(base_dir)
    workspace_config = _load_workspace_config(workspace_paths)

    selector = (project or workspace_config.current_project or "").strip()
    if not selector:
        raise CurrentProjectNotSetError(
            f"No current project is set in {workspace_paths.workspace_file}. "
            "Use 'doorae run --project <slug|path>' or update current_project."
        )

    project_dir, project_file = _resolve_project_reference(
        workspace_paths,
        workspace_config,
        selector,
    )
    project_config = _load_project_config(project_file)

    return ProjectRunContext(
        workspace=workspace_config,
        project=project_config,
        project_dir=project_dir,
        project_file=project_file,
        profiles_path=_resolve_project_config_path(
            project_dir,
            project_config.agent_profiles_path,
            field_name="agent_profiles_path",
        ),
        agendas_path=_resolve_project_config_path(
            project_dir,
            project_config.agendas_path,
            field_name="agendas_path",
        ),
    )


def _read_template_text(relative_path: Path) -> str:
    """Read a packaged scaffold template as UTF-8 text."""
    try:
        resource = resources.files(TEMPLATE_PACKAGE)
    except (ModuleNotFoundError, FileNotFoundError) as exc:
        raise MissingTemplateError(
            f"Could not load the packaged template package '{TEMPLATE_PACKAGE}'."
        ) from exc

    for part in relative_path.parts:
        resource = resource / part

    try:
        return resource.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise MissingTemplateError(
            f"Could not find the packaged template '{relative_path.as_posix()}'."
        ) from exc


def _load_workspace_config(paths: WorkspacePaths) -> WorkspaceConfig:
    """Load and validate workspace metadata from disk."""
    if not paths.workspace_file.exists():
        raise WorkspaceNotFoundError(
            f"Workspace not found at {paths.workspace_dir}. Run 'doorae init' first."
        )

    try:
        raw_config = yaml.safe_load(paths.workspace_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise WorkspaceError(
            f"Workspace metadata at {paths.workspace_file} is not valid YAML."
        ) from exc

    try:
        return WorkspaceConfig.from_dict(raw_config)
    except (TypeError, ValueError) as exc:
        raise WorkspaceError(
            f"Workspace metadata at {paths.workspace_file} is invalid."
        ) from exc


def _resolve_project_reference(
    workspace_paths: WorkspacePaths,
    workspace_config: WorkspaceConfig,
    selector: str,
) -> tuple[Path, Path]:
    """Resolve a slug or path selector to a concrete project directory and file."""
    if _looks_like_path(selector):
        candidate = Path(selector).expanduser()
        if not candidate.is_absolute():
            candidate = workspace_paths.root_dir / candidate
        candidate = candidate.resolve()
        project_file = candidate if candidate.name == "project.yaml" else candidate / "project.yaml"
        if not project_file.exists():
            raise ProjectNotFoundError(
                f"Project path '{selector}' does not contain a project.yaml file: {project_file}"
            )
        return project_file.parent, project_file

    project_paths = _resolve_project_paths(workspace_paths, workspace_config, selector)
    if not project_paths.project_file.exists():
        raise ProjectNotFoundError(
            f"Project '{selector}' was not found at {project_paths.project_dir}."
        )
    return project_paths.project_dir, project_paths.project_file


def _load_project_config(project_file: Path) -> ProjectConfig:
    """Load and validate project metadata from disk."""
    try:
        raw_config = yaml.safe_load(project_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProjectConfigError(
            f"Project metadata at {project_file} is not valid YAML."
        ) from exc

    try:
        return ProjectConfig.from_dict(raw_config)
    except (TypeError, ValueError) as exc:
        raise ProjectConfigError(
            f"Project metadata at {project_file} is invalid."
        ) from exc


def _resolve_project_config_path(
    project_dir: Path,
    raw_path: str,
    *,
    field_name: str,
) -> Path:
    """Resolve a project-local config file reference and ensure it exists."""
    config_path = Path(raw_path).expanduser()
    if not config_path.is_absolute():
        config_path = project_dir / config_path
    config_path = config_path.resolve()

    if not config_path.exists():
        raise ProjectConfigError(
            f"Project config '{field_name}' was not found: {config_path}"
        )
    if not config_path.is_file():
        raise ProjectConfigError(
            f"Project config '{field_name}' must point to a file: {config_path}"
        )
    return config_path


def _looks_like_path(selector: str) -> bool:
    """Return whether a project selector should be interpreted as a filesystem path."""
    candidate = Path(selector)
    if candidate.is_absolute():
        return True
    if len(candidate.parts) > 1:
        return True
    return selector.startswith((".", "~"))


def _resolve_project_paths(
    workspace_paths: WorkspacePaths,
    workspace_config: WorkspaceConfig,
    slug: str,
) -> ProjectPaths:
    """Resolve scaffold paths for a project within the workspace."""
    projects_root = Path(workspace_config.projects_dir)
    if not projects_root.is_absolute():
        projects_root = workspace_paths.root_dir / projects_root
    projects_root = projects_root.resolve()

    project_dir = projects_root / slug
    config_dir = project_dir / "config"
    return ProjectPaths(
        root_dir=workspace_paths.root_dir,
        workspace_dir=workspace_paths.workspace_dir,
        workspace_file=workspace_paths.workspace_file,
        projects_dir=projects_root,
        project_dir=project_dir,
        project_file=project_dir / "project.yaml",
        config_dir=config_dir,
        profiles_file=config_dir / "agent_profiles.yaml",
        agendas_file=config_dir / "agendas.yaml",
        mcp_servers_file=config_dir / "mcp_servers.json",
    )
