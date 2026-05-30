from __future__ import annotations

import re
from pathlib import Path

from pydantic import TypeAdapter

from app.llm import call_llm
from app.pipeline import load_items
from app.pipeline.state import set_pipeline_step
from app.prompts.service import render_prompt, validate_prompt_result
from app.projects import ensure_app_settings
from app.schemas import (
    DialogueLabel,
    DialogueLabelReviewItem,
    DialogueLabelReviewResponse,
    DialogueLabelUpdateRequest,
    GlossaryEntry,
    PipelineItem,
    PipelineRunResponse,
    PromptRenderRequest,
    PromptResultRequest,
    PromptScope,
    SegmentGlossaryEntry,
    SourceSegment,
)
from app.storage import read_json, resolve_project_path, write_json_atomic
from app.storage.helpers import db_volume_dir, read_json_default, work_volume_dir


dialogue_label_adapter = TypeAdapter(list[DialogueLabel])
glossary_adapter = TypeAdapter(list[GlossaryEntry])
segment_glossary_adapter = TypeAdapter(list[SegmentGlossaryEntry])
segment_adapter = TypeAdapter(list[SourceSegment])
ITEM_VOLUME_RE = re.compile(r"^v(?P<volume>\d+)_")

def _db_dir(project_root: str | Path, volume: int) -> Path:
    return db_volume_dir(project_root, volume)


def _work_dir(project_root: str | Path, volume: int) -> Path:
    return work_volume_dir(project_root, volume)


def _dialogue_labels_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "dialogue_labels.json"


def _glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "glossary.json"


def _series_glossary_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_glossary.json")


def _segment_glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "segment_glossary.json"


def _segments_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "segment", f"volume.{volume:02d}.segment.json")


def _load_labels(project_root: str | Path, volume: int) -> list[DialogueLabel]:
    return read_json_default(_dialogue_labels_path(project_root, volume), dialogue_label_adapter, [])


def _load_segments(project_root: str | Path, volume: int) -> list[SourceSegment]:
    return read_json(_segments_path(project_root, volume), segment_adapter)


def _character_entries(project_root: str | Path, volume: int) -> dict[str, GlossaryEntry]:
    entries: dict[str, GlossaryEntry] = {}
    for path in [_series_glossary_path(project_root), _glossary_path(project_root, volume)]:
        if not path.exists():
            continue
        for entry in read_json(path, glossary_adapter):
            if entry.type == "character":
                entries[entry.glossary_ID] = entry
    return entries


def _segment_character_ids(project_root: str | Path, volume: int, segment_id: str) -> set[str]:
    path = _segment_glossary_path(project_root, volume)
    if not path.exists():
        return set()
    ids: set[str] = set()
    for row in read_json(path, segment_glossary_adapter):
        if row.segment_ID == segment_id:
            ids.update(row.glossary_ID)
    characters = _character_entries(project_root, volume)
    return {glossary_id for glossary_id in ids if glossary_id in characters}


def _validate_character_id(
    value: str | None,
    characters: dict[str, GlossaryEntry],
    allowed_ids: set[str],
    field_name: str,
    item_id: str,
) -> None:
    if value is None:
        return
    if value not in characters:
        raise ValueError(f"{field_name} must be a character glossary_ID for {item_id}: {value}")
    if allowed_ids and value not in allowed_ids:
        raise ValueError(f"{field_name} must belong to the segment glossary for {item_id}: {value}")


def _normalize_label(
    row: DialogueLabel,
    item: PipelineItem,
    characters: dict[str, GlossaryEntry],
    allowed_ids: set[str],
) -> DialogueLabel:
    _validate_character_id(row.speaker, characters, allowed_ids, "speaker", row.item_ID)
    _validate_character_id(row.listener, characters, allowed_ids, "listener", row.item_ID)
    needs_review = row.human_review or row.speaker is None or row.listener is None
    if row.confidence is not None and row.confidence < 0.7:
        needs_review = True
    return DialogueLabel(
        item_ID=row.item_ID,
        segment_ID=item.segment_ID,
        speaker=row.speaker,
        listener=row.listener,
        confidence=row.confidence,
        human_review=needs_review,
        note=row.note,
    )


def extract_dialogue_labels(project_root: str | Path, volume: int) -> PipelineRunResponse:
    items = load_items(project_root, volume)
    items_by_id = {item.item_ID: item for item in items}
    dialogue_items_by_segment: dict[str, list[PipelineItem]] = {}
    for item in items:
        if item.type == "dialogue":
            dialogue_items_by_segment.setdefault(item.segment_ID, []).append(item)

    existing = _load_labels(project_root, volume)
    labels_by_item = {label.item_ID: label for label in existing}
    characters = _character_entries(project_root, volume)
    settings = ensure_app_settings()
    warnings: list[str] = []
    accepted = 0

    for segment in _load_segments(project_root, volume):
        dialogue_items = dialogue_items_by_segment.get(segment.segment_ID, [])
        if not dialogue_items:
            continue
        render = render_prompt(
            project_root,
            PromptRenderRequest(task="label_dialogue", scope=PromptScope(volume=volume, segment_ID=segment.segment_ID)),
        )
        raw_result = call_llm(settings, render.provider_slot, render.prompt)
        result_path = _work_dir(project_root, volume) / "llm_results" / f"label_dialogue_{segment.segment_ID}.txt"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(raw_result, encoding="utf-8")
        validation = validate_prompt_result(
            project_root,
            PromptResultRequest(
                task="label_dialogue",
                scope=PromptScope(volume=volume, segment_ID=segment.segment_ID),
                result_text=raw_result,
            ),
        )
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))
        allowed_ids = _segment_character_ids(project_root, volume, segment.segment_ID)
        returned_item_ids: set[str] = set()
        for row in dialogue_label_adapter.validate_python(validation.normalized or []):
            item = items_by_id.get(row.item_ID)
            if item is None:
                raise ValueError(f"Dialogue label item_ID does not exist: {row.item_ID}")
            if item.type != "dialogue":
                raise ValueError(f"Dialogue label item_ID is not a dialogue item: {row.item_ID}")
            if item.segment_ID != segment.segment_ID:
                raise ValueError(f"Dialogue label item_ID does not belong to segment {segment.segment_ID}: {row.item_ID}")
            labels_by_item[row.item_ID] = _normalize_label(row, item, characters, allowed_ids)
            returned_item_ids.add(row.item_ID)
            accepted += 1
        missing_items = [item for item in dialogue_items if item.item_ID not in returned_item_ids]
        for item in missing_items:
            labels_by_item[item.item_ID] = DialogueLabel(
                item_ID=item.item_ID,
                segment_ID=item.segment_ID,
                speaker=None,
                listener=None,
                human_review=True,
                note="Missing from LLM result",
            )
            warnings.append(f"missing_dialogue_label:{item.item_ID}")

    labels = sorted(labels_by_item.values(), key=lambda row: row.item_ID)
    write_json_atomic(
        _dialogue_labels_path(project_root, volume),
        labels,
        dialogue_label_adapter,
        project_root=project_root,
        backup=True,
    )
    review_count = sum(1 for row in labels if row.human_review)
    state = set_pipeline_step(
        project_root,
        volume,
        "dialogue_labels_extract",
        "needs_review" if review_count else "completed",
        f"{accepted} dialogue labels extracted",
        {"labels": len(labels), "human_review": review_count, "warnings": len(warnings)},
    )
    return PipelineRunResponse(
        volume=volume,
        pipeline_state=state,
        counts={"labels": len(labels), "human_review": review_count, "accepted": accepted},
        warnings=warnings,
    )


def get_dialogue_labels(project_root: str | Path, volume: int, segment_id: str | None = None) -> DialogueLabelReviewResponse:
    items = [item for item in load_items(project_root, volume) if item.type == "dialogue"]
    if segment_id:
        items = [item for item in items if item.segment_ID == segment_id]
    labels_by_item = {label.item_ID: label for label in _load_labels(project_root, volume)}
    segments = sorted({item.segment_ID for item in load_items(project_root, volume) if item.type == "dialogue"})
    rows = []
    for item in sorted(items, key=lambda row: row.item_ID):
        label = labels_by_item.get(item.item_ID)
        rows.append(
            DialogueLabelReviewItem(
                item_ID=item.item_ID,
                segment_ID=item.segment_ID,
                text=item.text,
                speaker=label.speaker if label else None,
                listener=label.listener if label else None,
                confidence=label.confidence if label else None,
                human_review=label.human_review if label else True,
                note=label.note if label else "",
            )
        )
    return DialogueLabelReviewResponse(
        volume=volume,
        segment_ID=segment_id,
        labels=rows,
        characters=list(_character_entries(project_root, volume).values()),
        segments=segments,
    )


def _volume_from_item_id(item_id: str) -> int:
    match = ITEM_VOLUME_RE.match(item_id)
    if not match:
        raise ValueError("item_ID must start with a canonical volume prefix like v01_")
    return int(match.group("volume"))


def update_dialogue_label(project_root: str | Path, item_id: str, request: DialogueLabelUpdateRequest) -> DialogueLabel:
    volume = _volume_from_item_id(item_id)
    items_by_id = {item.item_ID: item for item in load_items(project_root, volume)}
    item = items_by_id.get(item_id)
    if item is None:
        raise KeyError(f"Dialogue item not found: {item_id}")
    if item.type != "dialogue":
        raise ValueError(f"Item is not a dialogue item: {item_id}")

    labels = _load_labels(project_root, volume)
    current = next((label for label in labels if label.item_ID == item_id), None) or DialogueLabel(
        item_ID=item.item_ID,
        segment_ID=item.segment_ID,
        human_review=True,
    )
    updates = request.model_dump(exclude_unset=True)
    updated = current.model_copy(update=updates)
    updated = _normalize_label(
        updated,
        item,
        _character_entries(project_root, volume),
        _segment_character_ids(project_root, volume, item.segment_ID),
    )
    next_labels = [label for label in labels if label.item_ID != item_id]
    next_labels.append(updated)
    next_labels.sort(key=lambda label: label.item_ID)
    write_json_atomic(
        _dialogue_labels_path(project_root, volume),
        next_labels,
        dialogue_label_adapter,
        project_root=project_root,
        backup=True,
    )
    return updated
