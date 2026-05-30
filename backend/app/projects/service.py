from __future__ import annotations

from pathlib import Path
import os

from pydantic import TypeAdapter

from app import APP_VERSION
from app.prompts.defaults import DEFAULT_PROMPTS
from app.schemas import (
    AppSettings,
    IDCounter,
    ImportManifest,
    ProjectDetail,
    PipelineState,
    ProjectCreateRequest,
    ProjectCreateResponse,
    ProjectHealth,
    ProjectListItem,
    ProjectMetadata,
    ProjectMetadataUpdateRequest,
    ProjectOpenRequest,
    ProjectRegistry,
    RegisteredProject,
    ProjectSettings,
    ProjectSettingsUpdateRequest,
    WorkflowVolume,
    utc_now,
)
from app.storage import read_json, resolve_project_path, write_json_atomic, write_markdown_atomic


DEFAULT_PROJECT_DIRS = [
    "source",
    "segment",
    "prompt",
    "db",
    "db/volume.01",
    "work",
    "export",
    "backups",
    "logs",
]

SERIES_TABLES = {
    "db/series_glossary.json": [],
    "db/series_relationships.json": [],
}


def app_home() -> Path:
    override = os.environ.get("NOVEL_STUDIO_HOME")
    return Path(override).expanduser() if override else Path.home() / ".novel-studio"


def ensure_app_settings(settings_path: str | Path | None = None) -> AppSettings:
    path = Path(settings_path).expanduser() if settings_path else app_home() / "settings.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, AppSettings(), AppSettings)
    return read_json(path, AppSettings)


def registry_path(path: str | Path | None = None) -> Path:
    return Path(path).expanduser() if path else app_home() / "projects.json"


def load_project_registry(path: str | Path | None = None) -> ProjectRegistry:
    target = registry_path(path)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(target, ProjectRegistry(), ProjectRegistry)
    return read_json(target, ProjectRegistry)


def save_project_registry(registry: ProjectRegistry, path: str | Path | None = None) -> ProjectRegistry:
    target = registry_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return write_json_atomic(target, registry, ProjectRegistry)


def next_project_id(registry: ProjectRegistry) -> str:
    max_id = 0
    for project in registry.projects:
        suffix = project.project_ID.removeprefix("proj_")
        if suffix.isdigit():
            max_id = max(max_id, int(suffix))
    return f"proj_{max_id + 1:06d}"


def register_project(
    project_root: str | Path,
    metadata: ProjectMetadata,
    path: str | Path | None = None,
) -> ProjectRegistry:
    root = str(Path(project_root).expanduser().resolve())
    registry = load_project_registry(path)
    projects = [project for project in registry.projects if project.project_ID != metadata.project_ID and project.root != root]
    projects.append(
        RegisteredProject(
            project_ID=metadata.project_ID,
            root=root,
            name=metadata.name,
            updated_at=utc_now(),
        )
    )
    projects.sort(key=lambda project: project.updated_at, reverse=True)
    return save_project_registry(ProjectRegistry(projects=projects), path)


def load_project_metadata(project_root: str | Path) -> ProjectMetadata:
    return read_json(resolve_project_path(project_root, "project.json"), ProjectMetadata)


def load_project_settings(project_root: str | Path) -> ProjectSettings:
    return read_json(resolve_project_path(project_root, "settings.json"), ProjectSettings)


def ensure_project_structure(
    project_root: str | Path,
    metadata: ProjectMetadata | None = None,
    settings: ProjectSettings | None = None,
) -> ProjectCreateResponse:
    root = Path(project_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for directory in DEFAULT_PROJECT_DIRS:
        resolve_project_path(root, directory).mkdir(parents=True, exist_ok=True)

    metadata_path = resolve_project_path(root, "project.json")
    if metadata_path.exists():
        loaded_metadata = read_json(metadata_path, ProjectMetadata)
    else:
        loaded_metadata = metadata or ProjectMetadata(
            project_ID="proj_000001",
            name=root.name,
            genre="xianxia",
            source_language="zh",
            target_language="vi",
            created_at=utc_now(),
            app_version=APP_VERSION,
        )
        write_json_atomic(metadata_path, loaded_metadata, ProjectMetadata)

    settings_path = resolve_project_path(root, "settings.json")
    if settings_path.exists():
        loaded_settings = read_json(settings_path, ProjectSettings)
    else:
        loaded_settings = settings or ProjectSettings()
        write_json_atomic(settings_path, loaded_settings, ProjectSettings)

    counters_path = resolve_project_path(root, "db", "counters.json")
    if not counters_path.exists():
        write_json_atomic(counters_path, IDCounter(), IDCounter)

    for table_path, default_value in SERIES_TABLES.items():
        full_path = resolve_project_path(root, table_path)
        if not full_path.exists():
            write_json_atomic(full_path, default_value)

    for prompt_name, prompt_content in DEFAULT_PROMPTS.items():
        prompt_path = resolve_project_path(root, "prompt", prompt_name)
        if not prompt_path.exists():
            write_markdown_atomic(prompt_path, prompt_content)

    return ProjectCreateResponse(root=str(root), metadata=loaded_metadata, settings=loaded_settings)


def update_app_settings(settings: AppSettings) -> AppSettings:
    path = app_home() / "settings.json"
    return write_json_atomic(path, settings, AppSettings)


def update_project_settings(project_id: str, request: ProjectSettingsUpdateRequest) -> ProjectSettings:
    root = project_root_for_id(project_id)
    settings = ProjectSettings(
        max_subitem_tokens=request.max_subitem_tokens,
        batch_count_override=request.batch_count_override,
        prompt_folder=request.prompt_folder,
    )
    return write_json_atomic(resolve_project_path(root, "settings.json"), settings, ProjectSettings, project_root=root, backup=True)


def create_project(request: ProjectCreateRequest) -> ProjectCreateResponse:
    root = Path(request.root).expanduser().resolve()
    registry = load_project_registry()
    metadata = ProjectMetadata(
        project_ID=next_project_id(registry),
        name=request.name,
        genre=request.genre,
        source_language=request.source_language,
        target_language=request.target_language,
        notes=request.notes,
        created_at=utc_now(),
        app_version=APP_VERSION,
    )
    response = ensure_project_structure(root, metadata=metadata, settings=ProjectSettings())
    register_project(root, response.metadata)
    return response


def open_project(request: ProjectOpenRequest) -> ProjectCreateResponse:
    response = ensure_project_structure(request.root)
    register_project(response.root, response.metadata)
    return response


def project_root_for_id(project_id: str) -> Path:
    registry = load_project_registry()
    for project in registry.projects:
        if project.project_ID == project_id:
            return Path(project.root).expanduser().resolve()
    raise KeyError(f"Unknown project: {project_id}")


def list_projects() -> list[ProjectListItem]:
    registry = load_project_registry()
    items: list[ProjectListItem] = []
    for project in registry.projects:
        root = Path(project.root).expanduser().resolve()
        metadata_path = root / "project.json"
        if not metadata_path.exists():
            continue
        metadata = load_project_metadata(root)
        items.append(
            ProjectListItem(
                project_ID=metadata.project_ID,
                name=metadata.name,
                root=str(root),
                genre=metadata.genre,
                source_language=metadata.source_language,
                target_language=metadata.target_language,
            )
        )
    return items


def load_import_manifest(project_root: str | Path) -> ImportManifest:
    path = resolve_project_path(project_root, "work", "import_manifest.json")
    if not path.exists():
        return ImportManifest()
    return read_json(path, ImportManifest)


def calculate_project_health(project_root: str | Path) -> ProjectHealth:
    manifest = load_import_manifest(project_root)
    status_summary: dict[str, int] = {}
    for volume in manifest.volumes:
        status_summary[volume.status] = status_summary.get(volume.status, 0) + 1
    return ProjectHealth(
        volumes_imported=len(manifest.volumes),
        chapters_imported=sum(volume.chapters for volume in manifest.volumes),
        segments_imported=sum(volume.segments for volume in manifest.volumes),
        pipeline_status_summary=status_summary,
    )


def get_project_detail(project_id: str) -> ProjectDetail:
    root = project_root_for_id(project_id)
    return ProjectDetail(
        root=str(root),
        metadata=load_project_metadata(root),
        settings=load_project_settings(root),
        health=calculate_project_health(root),
    )


def update_project_metadata(project_id: str, request: ProjectMetadataUpdateRequest) -> ProjectDetail:
    root = project_root_for_id(project_id)
    current = load_project_metadata(root)
    updated = ProjectMetadata(
        project_ID=current.project_ID,
        name=request.name,
        genre=request.genre,
        source_language=request.source_language,
        target_language=request.target_language,
        notes=request.notes,
        created_at=current.created_at,
        app_version=current.app_version,
    )
    write_json_atomic(resolve_project_path(root, "project.json"), updated, ProjectMetadata, project_root=root, backup=True)
    register_project(root, updated)
    return get_project_detail(project_id)


def load_workflow_states(project_root: str | Path) -> list[WorkflowVolume]:
    root = Path(project_root).expanduser().resolve()
    work_root = resolve_project_path(root, "work")
    adapter = TypeAdapter(list[WorkflowVolume])
    if not work_root.exists():
        return []

    volumes: list[WorkflowVolume] = []
    for path in sorted(work_root.glob("volume.*/pipeline_state.json")):
        state = read_json(path, PipelineState)
        volume_id = state.volume_ID or path.parent.name.replace("volume.", "v")
        volumes.append(WorkflowVolume(volume=state.volume, volume_ID=volume_id, state=state))

    return adapter.validate_python([volume.model_dump(mode="json") for volume in volumes])
