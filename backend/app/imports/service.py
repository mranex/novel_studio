from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.schemas import (
    ImportCommitRequest,
    ImportCommitResponse,
    ImportFilePayload,
    ImportManifest,
    ImportManifestVolume,
    ImportPreviewRow,
    ImportValidateRequest,
    ImportValidationResponse,
    PipelineState,
    PipelineStepState,
    SourceChapter,
    SourceSegment,
    utc_now,
)
from app.storage import read_json, resolve_project_path, write_json_atomic, write_text_atomic


SOURCE_FILE_RE = re.compile(r"^volume\.(?P<volume>\d{2})\.json$")
SEGMENT_FILE_RE = re.compile(r"^volume\.(?P<volume>\d{2})\.segment\.json$")
SEGMENT_ID_RE = re.compile(r"^v(?P<volume>\d{2})_ch(?P<chapter>\d{3})_s(?P<segment>\d{3})$")

chapter_adapter = TypeAdapter(list[SourceChapter])
segment_adapter = TypeAdapter(list[SourceSegment])


class ImportSchemaError(ValueError):
    def __init__(self, messages: list[str]) -> None:
        super().__init__("\n".join(messages))
        self.messages = messages


FIELD_FIXES = {
    "chapter": '`chapter` must be a string ordinal such as "001". Do not use number 1; source and segment chapters must match exactly.',
    "name": '`name` must be a string. Use an empty string "" if the chapter has no title.',
    "content": '`content` must be a non-empty string containing the original source text.',
    "segment": '`segment` must be the segment ordinal inside the chapter, such as "001". Do not use legacy combined values like "c001_s001".',
    "segment_ID": '`segment_ID` is required and must be a canonical string such as "v01_ch001_s001", generated from volume, chapter, and segment.',
}


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _parse_volume(filename: str, pattern: re.Pattern[str]) -> int | None:
    match = pattern.match(Path(filename).name)
    if not match:
        return None
    return int(match.group("volume"))


def _json_loads(text: str, label: str) -> object:
    try:
        return json.loads(text.lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc.msg} at line {exc.lineno}.") from exc


def _value_type(value: object) -> str:
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def _display_value(value: object) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = repr(value)
    text = text.replace("\n", "\\n")
    if len(text) > 80:
        text = f"{text[:77]}..."
    if isinstance(value, str):
        return f'"{text}"'
    return text


def _format_schema_errors(label: str, errors: list[dict[str, object]]) -> list[str]:
    messages: list[str] = []
    for error in errors:
        loc = error.get("loc", ())
        if not isinstance(loc, tuple):
            loc = tuple(loc) if isinstance(loc, list) else (loc,)

        item_number = None
        field = "<root>"
        if loc and isinstance(loc[0], int):
            item_number = loc[0] + 1
            if len(loc) > 1:
                field = str(loc[1])
        elif loc:
            field = str(loc[-1])

        where = f"{label} item #{item_number}" if item_number is not None else f"{label} root"
        error_type = str(error.get("type", ""))
        fix = FIELD_FIXES.get(field, "Check this field against the import schema and remove unsupported or malformed data.")

        if error_type == "missing":
            messages.append(f"{where} field `{field}` is missing. Fix: {fix}")
            continue

        if error_type == "extra_forbidden":
            messages.append(f"{where} field `{field}` is not allowed by the import schema. Fix: remove this field.")
            continue

        current = error.get("input", None)
        messages.append(
            f"{where} field `{field}` has invalid value {_display_value(current)} "
            f"({_value_type(current)}). Fix: {fix}"
        )
    return messages


def _parse_source(text: str) -> list[SourceChapter]:
    data = _json_loads(text, "Source file")
    if not isinstance(data, list):
        raise ValueError('Source file root must be an array, for example: [{"chapter": "001", "name": "Chapter title", "content": "..."}].')
    try:
        return chapter_adapter.validate_python(data)
    except ValidationError as exc:
        raise ImportSchemaError(_format_schema_errors("Source", exc.errors())) from exc


def _parse_segment(text: str) -> list[SourceSegment]:
    data = _json_loads(text, "Segment file")
    if not isinstance(data, list):
        raise ValueError(
            'Segment file root must be an array, for example: [{"chapter": "001", "name": "Chapter title", "segment": "001", "segment_ID": "v01_ch001_s001", "content": "..."}].'
        )
    try:
        return segment_adapter.validate_python(data)
    except ValidationError as exc:
        raise ImportSchemaError(_format_schema_errors("Segment", exc.errors())) from exc


def validate_import(request: ImportValidateRequest) -> ImportValidationResponse:
    errors: list[str] = []
    warnings: list[str] = []
    preview: list[ImportPreviewRow] = []

    source_volume = _parse_volume(request.source_filename, SOURCE_FILE_RE)
    segment_volume = _parse_volume(request.segment_filename, SEGMENT_FILE_RE)
    if source_volume is None:
        errors.append("Source filename must match volume.XX.json.")
    if segment_volume is None:
        errors.append("Segment filename must match volume.XX.segment.json.")
    if source_volume is not None and segment_volume is not None and source_volume != segment_volume:
        errors.append("Source and segment filenames must use the same volume number.")

    try:
        chapters = _parse_source(request.source_text)
    except ImportSchemaError as exc:
        chapters = []
        errors.extend(exc.messages)
    except ValueError as exc:
        chapters = []
        errors.append(str(exc))

    try:
        segments = _parse_segment(request.segment_text)
    except ImportSchemaError as exc:
        segments = []
        errors.extend(exc.messages)
    except ValueError as exc:
        segments = []
        errors.append(str(exc))

    chapter_counts = Counter(chapter.chapter for chapter in chapters)
    for chapter, count in sorted(chapter_counts.items()):
        if count > 1:
            errors.append(f"Duplicate source chapter: {chapter}.")

    chapter_map = {chapter.chapter: chapter for chapter in chapters}
    for chapter in chapters:
        if not chapter.content.strip():
            errors.append(f"Source chapter {chapter.chapter} has empty content.")

    segment_id_counts = Counter(segment.segment_ID for segment in segments)
    for segment_id, count in sorted(segment_id_counts.items()):
        if count > 1:
            errors.append(f"Duplicate segment_ID: {segment_id}.")

    segments_by_chapter: dict[str, list[SourceSegment]] = defaultdict(list)
    for segment in segments:
        if not segment.content.strip():
            errors.append(f"Segment {segment.segment_ID} has empty content.")
        if segment.chapter not in chapter_map:
            errors.append(f"Segment {segment.segment_ID} references missing chapter {segment.chapter}.")
        expected_segment_volume = segment_volume or source_volume
        if expected_segment_volume is not None:
            match = SEGMENT_ID_RE.match(segment.segment_ID)
            if not match:
                if request.migrate_legacy_ids:
                    warnings.append(f"Legacy segment_ID found and would need migration: {segment.segment_ID}.")
                else:
                    errors.append(f"Invalid segment_ID format: {segment.segment_ID}.")
            elif int(match.group("volume")) != expected_segment_volume:
                errors.append(
                    f"Segment {segment.segment_ID} volume prefix does not match volume.{expected_segment_volume:02d}.segment.json."
                )
        segments_by_chapter[segment.chapter].append(segment)

    for chapter_number, chapter_segments in sorted(segments_by_chapter.items()):
        expected = [f"{index:03d}" for index in range(1, len(chapter_segments) + 1)]
        actual = [segment.segment for segment in chapter_segments]
        if actual != expected:
            warnings.append(f"Chapter {chapter_number} segment order is not consecutive from 001.")

        source = chapter_map.get(chapter_number)
        if not source:
            continue
        for segment in chapter_segments:
            if segment.name.strip() and source.name.strip() and segment.name.strip() != source.name.strip():
                warnings.append(f"Segment {segment.segment_ID} name differs from source chapter {chapter_number}.")
            if _normalize_text(segment.content) not in _normalize_text(source.content):
                warnings.append(f"Segment {segment.segment_ID} content is not an exact normalized substring of source.")

    for chapter in chapters:
        preview.append(
            ImportPreviewRow(
                volume=source_volume or segment_volume or 0,
                chapter=chapter.chapter,
                chapter_name=chapter.name,
                segment_count=len(segments_by_chapter.get(chapter.chapter, [])),
                warnings=[warning for warning in warnings if f" {chapter.chapter}" in warning],
            )
        )

    return ImportValidationResponse(
        ok=not errors,
        volume=source_volume if source_volume is not None and source_volume == segment_volume else source_volume,
        chapters=len(chapters),
        segments=len(segments),
        errors=errors,
        warnings=warnings,
        preview=preview,
    )


def load_manifest(project_root: str | Path) -> ImportManifest:
    path = resolve_project_path(project_root, "work", "import_manifest.json")
    if not path.exists():
        return ImportManifest()
    return read_json(path, ImportManifest)


def _save_manifest(project_root: str | Path, manifest: ImportManifest) -> ImportManifest:
    path = resolve_project_path(project_root, "work", "import_manifest.json")
    return write_json_atomic(path, manifest, ImportManifest, project_root=project_root, backup=True)


def _update_manifest(
    project_root: str | Path,
    volume: int,
    source_filename: str,
    segment_filename: str,
    chapters: int,
    segments: int,
) -> ImportManifest:
    manifest = load_manifest(project_root)
    next_volume = ImportManifestVolume(
        volume=volume,
        source_file=f"source/{Path(source_filename).name}",
        segment_file=f"segment/{Path(segment_filename).name}",
        chapters=chapters,
        segments=segments,
        validated_at=utc_now(),
        status="ready",
    )
    volumes = [item for item in manifest.volumes if item.volume != volume]
    volumes.append(next_volume)
    volumes.sort(key=lambda item: item.volume)
    return _save_manifest(project_root, ImportManifest(volumes=volumes))


def _write_pipeline_state(project_root: str | Path, volume: int) -> PipelineState:
    work_dir = resolve_project_path(project_root, "work", f"volume.{volume:02d}")
    work_dir.mkdir(parents=True, exist_ok=True)
    state = PipelineState(
        volume=volume,
        volume_ID=f"v{volume:02d}",
        steps=[
            PipelineStepState(name="import_source", status="completed", updated_at=utc_now()),
            PipelineStepState(name="skeleton", status="ready_for_skeleton", updated_at=utc_now()),
        ],
        updated_at=utc_now(),
    )
    write_json_atomic(work_dir / "pipeline_state.json", state, PipelineState)
    return state


def commit_import(project_root: str | Path, request: ImportCommitRequest) -> ImportCommitResponse:
    validation = validate_import(request)
    if not validation.ok or validation.volume is None:
        raise ValueError("\n".join(validation.errors or ["Import validation failed."]))

    volume = validation.volume
    resolve_project_path(project_root, "db", f"volume.{volume:02d}").mkdir(parents=True, exist_ok=True)
    resolve_project_path(project_root, "work", f"volume.{volume:02d}").mkdir(parents=True, exist_ok=True)

    source_path = resolve_project_path(project_root, "source", Path(request.source_filename).name)
    segment_path = resolve_project_path(project_root, "segment", Path(request.segment_filename).name)
    write_text_atomic(source_path, request.source_text, project_root=project_root, backup=True)
    write_text_atomic(segment_path, request.segment_text, project_root=project_root, backup=True)

    manifest = _update_manifest(
        project_root,
        volume,
        request.source_filename,
        request.segment_filename,
        validation.chapters,
        validation.segments,
    )
    pipeline_state = _write_pipeline_state(project_root, volume)
    return ImportCommitResponse(validation=validation, manifest=manifest, pipeline_state=pipeline_state)


def commit_source_file(project_root: str | Path, payload: ImportFilePayload) -> ImportValidationResponse:
    volume = _parse_volume(payload.filename, SOURCE_FILE_RE)
    errors: list[str] = []
    if volume is None:
        errors.append("Source filename must match volume.XX.json.")
    try:
        chapters = _parse_source(payload.text)
    except ImportSchemaError as exc:
        chapters = []
        errors.extend(exc.messages)
    except ValueError as exc:
        chapters = []
        errors.append(str(exc))
    chapter_counts = Counter(chapter.chapter for chapter in chapters)
    for chapter, count in sorted(chapter_counts.items()):
        if count > 1:
            errors.append(f"Duplicate source chapter: {chapter}.")
    for chapter in chapters:
        if not chapter.content.strip():
            errors.append(f"Source chapter {chapter.chapter} has empty content.")

    response = ImportValidationResponse(
        ok=not errors,
        volume=volume,
        chapters=len(chapters),
        segments=0,
        errors=errors,
        warnings=[],
        preview=[
            ImportPreviewRow(
                volume=volume or 0,
                chapter=chapter.chapter,
                chapter_name=chapter.name,
                segment_count=0,
                warnings=[],
            )
            for chapter in chapters
        ],
    )
    if response.ok:
        path = resolve_project_path(project_root, "source", Path(payload.filename).name)
        write_text_atomic(path, payload.text, project_root=project_root, backup=True)
    return response


def commit_segment_file(project_root: str | Path, payload: ImportFilePayload) -> ImportCommitResponse:
    volume = _parse_volume(payload.filename, SEGMENT_FILE_RE)
    if volume is None:
        raise ValueError("Segment filename must match volume.XX.segment.json.")
    source_filename = f"volume.{volume:02d}.json"
    source_path = resolve_project_path(project_root, "source", source_filename)
    if not source_path.exists():
        raise ValueError(f"Import {source_filename} before importing segments.")
    source_text = source_path.read_text(encoding="utf-8-sig")
    request = ImportCommitRequest(
        source_filename=source_filename,
        source_text=source_text,
        segment_filename=payload.filename,
        segment_text=payload.text,
    )
    return commit_import(project_root, request)
