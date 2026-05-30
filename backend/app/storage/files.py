from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def resolve_project_path(project_root: str | Path, *parts: str | Path) -> Path:
    root = Path(project_root).expanduser().resolve()
    target = root.joinpath(*parts).resolve()
    common = os.path.commonpath([str(root), str(target)])
    if common != str(root):
        raise ValueError(f"Path escapes project root: {target}")
    return target


def _validate(data: Any, schema: Any | None) -> Any:
    if schema is None:
        return data
    if hasattr(schema, "validate_python"):
        return schema.validate_python(data)
    if hasattr(schema, "model_validate"):
        return schema.model_validate(data)
    raise TypeError("schema must be a Pydantic model or TypeAdapter")


def read_json(path: str | Path, schema: Any | None = None, default: Any | None = None) -> Any:
    target = Path(path)
    if not target.exists():
        if default is not None:
            return default
        raise FileNotFoundError(target)
    with target.open("r", encoding="utf-8-sig") as file:
        data = json.load(file)
    return _validate(data, schema)


def backup_file(path: str | Path, project_root: str | Path) -> Path | None:
    source = Path(path)
    if not source.exists():
        return None
    root = Path(project_root).expanduser().resolve()
    backup_root = resolve_project_path(root, "backups")
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    backup_name = f"{timestamp}_{source.name}"
    backup_path = backup_root / backup_name
    shutil.copy2(source, backup_path)
    return backup_path


def write_json_atomic(
    path: str | Path,
    data: Any,
    schema: Any | None = None,
    *,
    project_root: str | Path | None = None,
    backup: bool = False,
) -> Any:
    validated = _validate(data, schema)
    if schema is not None and hasattr(schema, "dump_python"):
        serializable = schema.dump_python(validated, mode="json")
    elif hasattr(validated, "model_dump"):
        serializable = validated.model_dump(mode="json")
    else:
        serializable = data
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        if project_root is None:
            raise ValueError("project_root is required when backup=True")
        backup_file(target, project_root)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            json.dump(serializable, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return validated


def read_markdown(path: str | Path, default: str | None = None) -> str:
    target = Path(path)
    if not target.exists():
        if default is not None:
            return default
        raise FileNotFoundError(target)
    return target.read_text(encoding="utf-8-sig")


def write_markdown_atomic(
    path: str | Path,
    content: str,
    *,
    project_root: str | Path | None = None,
    backup: bool = False,
) -> None:
    if not isinstance(content, str):
        raise TypeError("Markdown content must be a string")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        if project_root is None:
            raise ValueError("project_root is required when backup=True")
        backup_file(target, project_root)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            if content and not content.endswith("\n"):
                file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def write_text_atomic(
    path: str | Path,
    content: str,
    *,
    project_root: str | Path | None = None,
    backup: bool = False,
) -> None:
    if not isinstance(content, str):
        raise TypeError("Text content must be a string")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        if project_root is None:
            raise ValueError("project_root is required when backup=True")
        backup_file(target, project_root)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
