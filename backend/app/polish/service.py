from __future__ import annotations

import html
from pathlib import Path

from pydantic import TypeAdapter

from app.schemas import (
    ExportRequest,
    ExportResponse,
    PipelineItem,
    PolishChapterPreview,
    PolishOverride,
    PolishOverrideRequest,
    PolishPreviewItem,
    SegmentSkeleton,
    SourceChapter,
    SourceSegment,
    Translation,
    utc_now,
)
from app.storage import read_json, resolve_project_path, write_json_atomic, write_text_atomic
from app.storage.helpers import read_json_default, volume_dir


chapter_adapter = TypeAdapter(list[SourceChapter])
segment_adapter = TypeAdapter(list[SourceSegment])
skeleton_adapter = TypeAdapter(list[SegmentSkeleton])
item_adapter = TypeAdapter(list[PipelineItem])
translation_adapter = TypeAdapter(list[Translation])
override_adapter = TypeAdapter(list[PolishOverride])

def _source_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "source", f"volume.{volume:02d}.json")


def _segment_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "segment", f"volume.{volume:02d}.segment.json")


def _work_path(project_root: str | Path, volume: int, filename: str) -> Path:
    return resolve_project_path(project_root, "work", volume_dir(volume), filename)


def _db_path(project_root: str | Path, volume: int, filename: str) -> Path:
    path = resolve_project_path(project_root, "db", volume_dir(volume))
    path.mkdir(parents=True, exist_ok=True)
    return path / filename


def _load_chapters(project_root: str | Path, volume: int) -> list[SourceChapter]:
    return read_json(_source_path(project_root, volume), chapter_adapter)


def _load_segments(project_root: str | Path, volume: int) -> list[SourceSegment]:
    return read_json(_segment_path(project_root, volume), segment_adapter)


def _load_skeleton(project_root: str | Path, volume: int) -> list[SegmentSkeleton]:
    return read_json(_work_path(project_root, volume, "segment_skeleton.json"), skeleton_adapter)


def _load_items(project_root: str | Path, volume: int) -> list[PipelineItem]:
    return read_json(_work_path(project_root, volume, "segment_flesh.json"), item_adapter)


def _load_translations(project_root: str | Path, volume: int) -> list[Translation]:
    return read_json_default(_db_path(project_root, volume, "translations.json"), translation_adapter, [])


def _load_overrides(project_root: str | Path, volume: int) -> list[PolishOverride]:
    return read_json_default(_db_path(project_root, volume, "polish_overrides.json"), override_adapter, [])


def _chapter_preview(project_root: str | Path, volume: int, chapter: str) -> PolishChapterPreview:
    chapters = {row.chapter: row for row in _load_chapters(project_root, volume)}
    chapter_row = chapters.get(chapter)
    if chapter_row is None:
        raise KeyError(f"Chapter not found: {chapter}")
    segments = [row for row in _load_segments(project_root, volume) if row.chapter == chapter]
    skeleton_by_segment = {row.segment_ID: row for row in _load_skeleton(project_root, volume)}
    items_by_id = {row.item_ID: row for row in _load_items(project_root, volume)}
    translations = {row.item_ID: row for row in _load_translations(project_root, volume)}
    overrides = {row.item_ID: row for row in _load_overrides(project_root, volume)}

    preview_items: list[PolishPreviewItem] = []
    paragraphs: list[str] = []
    for segment in segments:
        skeleton = skeleton_by_segment.get(segment.segment_ID)
        if not skeleton:
            continue
        for item_id in skeleton.items:
            item = items_by_id.get(item_id)
            if not item:
                continue
            translation = translations.get(item_id)
            override = overrides.get(item_id)
            missing = translation is None and override is None
            text = override.text if override else (translation.trans_text if translation else f"[MISSING TRANSLATION: {item_id}]")
            paragraphs.append(text)
            preview_items.append(
                PolishPreviewItem(
                    item_ID=item.item_ID,
                    segment_ID=item.segment_ID,
                    type=item.type,
                    source_text=item.text,
                    translation_text=translation.trans_text if translation else None,
                    polished_text=override.text if override else None,
                    preview_text=text,
                    missing=missing,
                )
            )
    return PolishChapterPreview(
        volume=volume,
        chapter=chapter,
        chapter_name=chapter_row.name,
        text="\n\n".join(paragraphs),
        items=preview_items,
    )


def get_polish_preview(project_root: str | Path, volume: int, chapter: str | None = None) -> PolishChapterPreview:
    if chapter is None:
        chapters = _load_chapters(project_root, volume)
        if not chapters:
            raise KeyError("No chapters found.")
        chapter = chapters[0].chapter
    return _chapter_preview(project_root, volume, chapter)


def save_polish_override(project_root: str | Path, volume: int, item_id: str, request: PolishOverrideRequest) -> PolishOverride:
    item_ids = {row.item_ID for row in _load_items(project_root, volume)}
    if item_id not in item_ids:
        raise KeyError(f"Item not found: {item_id}")
    rows = [row for row in _load_overrides(project_root, volume) if row.item_ID != item_id]
    updated = PolishOverride(item_ID=item_id, text=request.text, updated_at=utc_now())
    rows.append(updated)
    rows.sort(key=lambda row: row.item_ID)
    write_json_atomic(_db_path(project_root, volume, "polish_overrides.json"), rows, override_adapter, project_root=project_root, backup=True)
    return updated


def _volume_numbers(project_root: str | Path) -> list[int]:
    segment_root = resolve_project_path(project_root, "segment")
    if not segment_root.exists():
        return []
    volumes = []
    for path in segment_root.glob("volume.*.segment.json"):
        try:
            volumes.append(int(path.name.split(".")[1]))
        except (IndexError, ValueError):
            continue
    return sorted(set(volumes))


def _render_volume(project_root: str | Path, volume: int, fmt: str) -> tuple[str, int]:
    parts: list[str] = []
    missing = 0
    for chapter in _load_chapters(project_root, volume):
        preview = _chapter_preview(project_root, volume, chapter.chapter)
        missing += sum(1 for item in preview.items if item.missing)
        if fmt == "md":
            parts.append(f"# {chapter.name or 'Chapter ' + chapter.chapter}\n\n{preview.text}")
        elif fmt == "html":
            title = html.escape(chapter.name or f"Chapter {chapter.chapter}")
            paragraphs = "\n".join(f"<p>{html.escape(item.preview_text)}</p>" for item in preview.items)
            parts.append(f"<section><h1>{title}</h1>\n{paragraphs}</section>")
        else:
            parts.append(f"{chapter.name or 'Chapter ' + chapter.chapter}\n\n{preview.text}")
    return "\n\n".join(parts), missing


def export_project(project_root: str | Path, request: ExportRequest) -> ExportResponse:
    if request.scope == "series":
        volumes = _volume_numbers(project_root)
    elif request.scope == "selected_volumes":
        volumes = request.volumes
    else:
        volumes = request.volumes[:1]
    if not volumes:
        raise ValueError("At least one volume is required for export.")

    rendered: list[str] = []
    missing = 0
    for volume in volumes:
        text, volume_missing = _render_volume(project_root, volume, request.format)
        rendered.append(text)
        missing += volume_missing

    content = "\n\n".join(rendered)
    if request.format == "html":
        content = "<!doctype html>\n<html><head><meta charset=\"utf-8\"><title>Novel Export</title></head><body>\n" + content + "\n</body></html>\n"
    export_root = resolve_project_path(project_root, "export")
    export_root.mkdir(parents=True, exist_ok=True)
    if len(volumes) == 1 and request.scope == "volume":
        filename = f"volume.{volumes[0]:02d}.{request.format}"
    else:
        filename = f"{request.scope}.{request.format}"
    path = export_root / filename
    write_text_atomic(path, content)
    return ExportResponse(format=request.format, scope=request.scope, path=str(path), volumes=volumes, missing_translations=missing)
