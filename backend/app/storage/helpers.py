from __future__ import annotations

from pathlib import Path
from typing import Any

from app.storage.files import read_json, resolve_project_path


def volume_dir(volume: int) -> str:
    return f"volume.{volume:02d}"


def read_json_default(path: str | Path, schema: Any | None, default: Any) -> Any:
    target = Path(path)
    if not target.exists():
        if schema is not None and hasattr(schema, "validate_python"):
            return schema.validate_python(default)
        if schema is not None and hasattr(schema, "model_validate"):
            return schema.model_validate(default)
        return default
    return read_json(target, schema)


def db_volume_dir(project_root: str | Path, volume: int) -> Path:
    path = resolve_project_path(project_root, "db", volume_dir(volume))
    path.mkdir(parents=True, exist_ok=True)
    return path


def work_volume_dir(project_root: str | Path, volume: int) -> Path:
    path = resolve_project_path(project_root, "work", volume_dir(volume))
    path.mkdir(parents=True, exist_ok=True)
    return path
