from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .ids import normalize_volume
from .models import Chapter, Segment
from .validation import validate_chapters, validate_segments


def output_filenames(volume_number: str | int) -> tuple[str, str]:
    volume = normalize_volume(volume_number)
    return f"volume.{volume:02d}.json", f"volume.{volume:02d}.segment.json"


def _atomic_write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def export_volume(path: str | Path, chapters: list[Chapter]) -> Path:
    result = validate_chapters(chapters)
    if not result.ok:
        raise ValueError("\n".join(result.errors))
    target = Path(path)
    _atomic_write_json(target, [chapter.to_json() for chapter in chapters])
    return target


def export_segments(
    path: str | Path,
    chapters: list[Chapter],
    segments: list[Segment],
    volume_number: str | int,
) -> Path:
    result = validate_segments(chapters, segments, volume_number)
    if not result.ok:
        raise ValueError("\n".join(result.errors))
    target = Path(path)
    _atomic_write_json(target, [segment.to_json() for segment in segments])
    return target


def export_all(
    directory: str | Path,
    chapters: list[Chapter],
    segments: list[Segment],
    volume_number: str | int,
) -> tuple[Path, Path]:
    volume_name, segment_name = output_filenames(volume_number)
    root = Path(directory)
    volume_path = export_volume(root / volume_name, chapters)
    segment_path = export_segments(root / segment_name, chapters, segments, volume_number)
    return volume_path, segment_path
