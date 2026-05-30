from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter

from app.ids import allocate_id
from app.llm import call_llm
from app.pipeline.state import set_pipeline_step
from app.prompts.service import render_prompt, validate_prompt_result
from app.projects import ensure_app_settings
from app.schemas import (
    GlossaryEntry,
    PipelineRunResponse,
    PromptRelationshipResult,
    PromptRenderRequest,
    PromptResultRequest,
    PromptScope,
    Relationship,
    RelationshipCanvasResponse,
    RelationshipCreateRequest,
    RelationshipEdge,
    RelationshipLayoutNode,
    RelationshipLayoutRequest,
    RelationshipNode,
    RelationshipUpdateRequest,
    SourceSegment,
    TimelinePoint,
)
from app.storage import read_json, resolve_project_path, write_json_atomic
from app.storage.helpers import db_volume_dir, read_json_default, work_volume_dir


Scope = Literal["series", "volume"]

relationship_adapter = TypeAdapter(list[Relationship])
relationship_result_adapter = TypeAdapter(list[PromptRelationshipResult])
glossary_adapter = TypeAdapter(list[GlossaryEntry])
segment_adapter = TypeAdapter(list[SourceSegment])
layout_adapter = TypeAdapter(list[RelationshipLayoutNode])
TIME_KEY_RE = re.compile(r"^v(?P<volume>\d+)_ch(?P<chapter>\d+)_s(?P<segment>\d+)$")
TYPE_PRIORITY = ["enemy", "love", "family", "ally", "neutral", "unknown"]

def _db_dir(project_root: str | Path, volume: int) -> Path:
    return db_volume_dir(project_root, volume)


def _work_dir(project_root: str | Path, volume: int) -> Path:
    return work_volume_dir(project_root, volume)


def _relationships_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "relationships.json"


def _series_relationships_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_relationships.json")


def _glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "glossary.json"


def _series_glossary_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_glossary.json")


def _segment_glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "segment_glossary.json"


def _segments_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "segment", f"volume.{volume:02d}.segment.json")


def _layout_path(project_root: str | Path, volume: int) -> Path:
    return _work_dir(project_root, volume) / "relationship_canvas_layout.json"


def _load_relationships(project_root: str | Path, volume: int) -> list[Relationship]:
    return read_json_default(_relationships_path(project_root, volume), relationship_adapter, [])


def _load_series_relationships(project_root: str | Path) -> list[Relationship]:
    return read_json_default(_series_relationships_path(project_root), relationship_adapter, [])


def _load_glossary(project_root: str | Path, volume: int) -> list[GlossaryEntry]:
    return read_json_default(_glossary_path(project_root, volume), glossary_adapter, [])


def _load_series_glossary(project_root: str | Path) -> list[GlossaryEntry]:
    return read_json_default(_series_glossary_path(project_root), glossary_adapter, [])


def _load_segments(project_root: str | Path, volume: int) -> list[SourceSegment]:
    return read_json(_segments_path(project_root, volume), segment_adapter)


def _time_from_key(time_key: str) -> TimelinePoint:
    match = TIME_KEY_RE.match(time_key)
    if not match:
        raise ValueError("time_key must look like v01_ch001_s001")
    return TimelinePoint(
        volume=int(match.group("volume")),
        chapter=int(match.group("chapter")),
        segment=int(match.group("segment")),
        key=time_key,
    )


def _time_tuple(time: TimelinePoint) -> tuple[int, int, int]:
    return (time.volume, time.chapter or 0, time.segment or 0)


def _relationship_sort_key(row: Relationship) -> tuple[int, int, int, str]:
    return (*_time_tuple(row.time), row.relationship_ID)


def _timeline_key(time: TimelinePoint) -> str:
    if time.key:
        return time.key
    return f"v{time.volume:02d}_ch{time.chapter or 0:03d}_s{time.segment or 0:03d}"


def _volume_numbers(project_root: str | Path, through_volume: int | None = None) -> list[int]:
    segment_root = resolve_project_path(project_root, "segment")
    if not segment_root.exists():
        return []
    volumes = []
    for path in segment_root.glob("volume.*.segment.json"):
        try:
            volume = int(path.name.split(".")[1])
        except (IndexError, ValueError):
            continue
        if through_volume is None or volume <= through_volume:
            volumes.append(volume)
    return sorted(set(volumes))


def _relationship_sources(project_root: str | Path, volume: int, scope: Scope) -> list[Relationship]:
    records: list[Relationship] = []
    if scope == "series":
        records.extend(_load_series_relationships(project_root))
        for current_volume in _volume_numbers(project_root, volume):
            records.extend(_load_relationships(project_root, current_volume))
    else:
        records.extend(_load_relationships(project_root, volume))
    return records


def _timeline_keys(project_root: str | Path, volume: int, scope: Scope) -> list[str]:
    keys: list[str] = []
    volumes = _volume_numbers(project_root, volume) if scope == "series" else [volume]
    for current_volume in volumes:
        path = _segments_path(project_root, current_volume)
        if not path.exists():
            continue
        keys.extend(segment.segment_ID for segment in read_json(path, segment_adapter))
    return sorted(set(keys), key=lambda key: _time_tuple(_time_from_key(key)) if TIME_KEY_RE.match(key) else (999, 999, 999))


def _characters(project_root: str | Path, volume: int, scope: Scope) -> dict[str, GlossaryEntry]:
    entries: dict[str, GlossaryEntry] = {}
    if scope == "series":
        for entry in _load_series_glossary(project_root):
            if entry.type == "character":
                entries[entry.glossary_ID] = entry
        volumes = _volume_numbers(project_root, volume)
    else:
        volumes = [volume]
    for current_volume in volumes:
        for entry in _load_glossary(project_root, current_volume):
            if entry.type == "character":
                entries[entry.glossary_ID] = entry
    return entries


def _segment_character_ids(project_root: str | Path, volume: int, segment_id: str) -> set[str]:
    path = _segment_glossary_path(project_root, volume)
    if not path.exists():
        return set()
    rows = read_json(path, default=[])
    glossary_ids: set[str] = set()
    for row in rows:
        if row.get("segment_ID") == segment_id:
            glossary_ids.update(row.get("glossary_ID") or [])
    characters = _characters(project_root, volume, "series")
    return {glossary_id for glossary_id in glossary_ids if glossary_id in characters}


def _validate_character_pair(characters: dict[str, GlossaryEntry], speaker: str, listener: str) -> None:
    if speaker not in characters:
        raise ValueError(f"speaker must be a character glossary_ID: {speaker}")
    if listener not in characters:
        raise ValueError(f"listener must be a character glossary_ID: {listener}")
    if speaker == listener:
        raise ValueError("speaker and listener must be different character IDs")


def _same_state(left: Relationship, right: Relationship) -> bool:
    return (
        left.type == right.type
        and left.relationship == right.relationship
        and left.pronoun == right.pronoun
        and sorted(left.alias_pronoun) == sorted(right.alias_pronoun)
    )


def _known(value: str | None) -> bool:
    return bool(value and value.strip())


def _mark_conflict_if_needed(previous: Relationship | None, current: Relationship) -> Relationship:
    if previous is None:
        return current
    null_collision = (
        not _known(current.pronoun)
        and _known(previous.pronoun)
        and (current.type == previous.type or current.relationship == previous.relationship)
    )
    partial_duplicate = (
        (current.type == previous.type and current.pronoun != previous.pronoun)
        or (_known(current.pronoun) and current.pronoun == previous.pronoun and current.type != previous.type)
        or (current.type == previous.type and current.relationship != previous.relationship)
        or null_collision
    )
    if partial_duplicate:
        return current.model_copy(update={"conflict": True, "human_review": True})
    return current


def merge_relationship_records(records: list[Relationship]) -> list[Relationship]:
    latest: dict[tuple[str, str], Relationship] = {}
    merged: list[Relationship] = []
    seen_ids: set[str] = set()
    for record in sorted(records, key=_relationship_sort_key):
        if record.relationship_ID in seen_ids:
            continue
        key = (record.speaker, record.listener)
        previous = latest.get(key)
        if previous and _same_state(previous, record):
            continue
        next_record = _mark_conflict_if_needed(previous, record)
        latest[key] = next_record
        merged.append(next_record)
        seen_ids.add(next_record.relationship_ID)
    return merged


def _normalize_prompt_relationship(project_root: str | Path, row: PromptRelationshipResult, fallback_segment_id: str) -> Relationship:
    time = row.time
    if time.key is None:
        time = TimelinePoint(volume=time.volume, chapter=time.chapter, segment=time.segment, key=fallback_segment_id)
    return Relationship(
        relationship_ID=row.relationship_ID or allocate_id(project_root, "relationship"),
        speaker=row.speaker,
        listener=row.listener,
        type=row.type,
        relationship=row.relationship,
        pronoun=row.pronoun,
        alias_pronoun=row.alias_pronoun,
        time=time,
        source_segment_ID=row.source_segment_ID or fallback_segment_id,
        human_review=row.human_review,
        conflict=row.conflict,
        note=row.note,
    )


def extract_relationships(project_root: str | Path, volume: int) -> PipelineRunResponse:
    segments = _load_segments(project_root, volume)
    existing = _load_relationships(project_root, volume)
    existing_keys = {(row.source_segment_ID, row.speaker, row.listener, row.type, row.relationship, row.pronoun or "") for row in existing}
    characters = _characters(project_root, volume, "series")
    settings = ensure_app_settings()
    accepted: list[Relationship] = []
    warnings: list[str] = []

    for segment in segments:
        valid_ids = _segment_character_ids(project_root, volume, segment.segment_ID)
        if len(valid_ids) < 2:
            warnings.append(f"not_enough_segment_characters:{segment.segment_ID}")
            continue
        render = render_prompt(
            project_root,
            PromptRenderRequest(task="extract_relationship", scope=PromptScope(volume=volume, segment_ID=segment.segment_ID)),
        )
        raw_result = call_llm(settings, render.provider_slot, render.prompt)
        result_path = _work_dir(project_root, volume) / "llm_results" / f"extract_relationship_{segment.segment_ID}.txt"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(raw_result, encoding="utf-8")
        validation = validate_prompt_result(
            project_root,
            PromptResultRequest(
                task="extract_relationship",
                scope=PromptScope(volume=volume, segment_ID=segment.segment_ID),
                result_text=raw_result,
            ),
        )
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))
        rows = relationship_result_adapter.validate_python(validation.normalized or [])
        for row in rows:
            record = _normalize_prompt_relationship(project_root, row, segment.segment_ID)
            if record.speaker not in valid_ids or record.listener not in valid_ids:
                warnings.append(f"invalid_segment_character:{segment.segment_ID}:{record.speaker}->{record.listener}")
                continue
            _validate_character_pair(characters, record.speaker, record.listener)
            key = (record.source_segment_ID, record.speaker, record.listener, record.type, record.relationship, record.pronoun or "")
            if key in existing_keys:
                continue
            accepted.append(record)
            existing_keys.add(key)

    all_rows = merge_relationship_records(existing + accepted)
    write_json_atomic(
        _relationships_path(project_root, volume),
        all_rows,
        relationship_adapter,
        project_root=project_root,
        backup=True,
    )
    state = set_pipeline_step(
        project_root,
        volume,
        "relationships_extract",
        "needs_review",
        f"{len(accepted)} relationship records extracted",
        {"relationship_rows": len(all_rows), "new_rows": len(accepted), "warnings": len(warnings)},
    )
    return PipelineRunResponse(
        volume=volume,
        pipeline_state=state,
        counts={"relationship_rows": len(all_rows), "new_rows": len(accepted)},
        warnings=warnings,
    )


def merge_relationships(project_root: str | Path, volume: int) -> PipelineRunResponse:
    before = _load_relationships(project_root, volume)
    after = merge_relationship_records(before)
    write_json_atomic(
        _relationships_path(project_root, volume),
        after,
        relationship_adapter,
        project_root=project_root,
        backup=True,
    )
    conflicts = sum(1 for row in after if row.conflict)
    state = set_pipeline_step(
        project_root,
        volume,
        "relationships_merge",
        "needs_review" if conflicts else "completed",
        f"{len(before) - len(after)} duplicate relationship records removed",
        {"relationship_rows": len(after), "conflicts": conflicts},
    )
    return PipelineRunResponse(
        volume=volume,
        pipeline_state=state,
        counts={"relationship_rows": len(after), "conflicts": conflicts},
        warnings=[],
    )


def get_relationship_state(project_root: str | Path, time_key: str, scope: Scope = "series") -> list[Relationship]:
    cursor = _time_from_key(time_key)
    records = _relationship_sources(project_root, cursor.volume, scope)
    state: dict[tuple[str, str], Relationship] = {}
    for record in sorted(records, key=_relationship_sort_key):
        if _time_tuple(record.time) <= _time_tuple(cursor):
            state[(record.speaker, record.listener)] = record
    return sorted(state.values(), key=lambda row: (row.speaker, row.listener))


def _edge_type(rows: list[Relationship]) -> str:
    if any(row.conflict for row in rows):
        return "conflict"
    for type_value in TYPE_PRIORITY:
        if any(row.type == type_value for row in rows):
            return type_value
    return "unknown"


def _edge_label(rows: list[Relationship]) -> str:
    parts = []
    for row in sorted(rows, key=lambda item: (item.speaker, item.listener)):
        label = row.relationship or row.type
        if row.pronoun:
            label = f"{label} / {row.pronoun}"
        parts.append(label)
    return " | ".join(parts)


def _layout_positions(project_root: str | Path, volume: int) -> dict[str, RelationshipLayoutNode]:
    path = _layout_path(project_root, volume)
    if not path.exists():
        return {}
    return {node.id: node for node in read_json(path, layout_adapter)}


def _default_position(index: int, count: int) -> tuple[float, float]:
    if count <= 1:
        return (0.0, 0.0)
    radius = max(180.0, min(420.0, count * 56.0))
    angle = (2 * math.pi * index) / count
    return (math.cos(angle) * radius, math.sin(angle) * radius)


def get_relationship_canvas(project_root: str | Path, time_key: str, scope: Scope = "series") -> RelationshipCanvasResponse:
    cursor = _time_from_key(time_key)
    relationships = get_relationship_state(project_root, time_key, scope)
    characters = _characters(project_root, cursor.volume, scope)
    involved = {row.speaker for row in relationships} | {row.listener for row in relationships}
    node_ids = sorted(set(characters.keys()) | involved)
    layout = _layout_positions(project_root, cursor.volume)
    nodes: list[RelationshipNode] = []
    for index, glossary_id in enumerate(node_ids):
        entry = characters.get(glossary_id)
        fallback_x, fallback_y = _default_position(index, max(len(node_ids), 1))
        saved = layout.get(glossary_id)
        conflict = any(row.conflict for row in relationships if row.speaker == glossary_id or row.listener == glossary_id)
        nodes.append(
            RelationshipNode(
                id=glossary_id,
                label=(entry.trans or entry.source) if entry else glossary_id,
                source=entry.source if entry else glossary_id,
                trans=entry.trans if entry else "",
                conflict=conflict,
                x=saved.x if saved else fallback_x,
                y=saved.y if saved else fallback_y,
            )
        )

    grouped_edges: dict[tuple[str, str], list[Relationship]] = defaultdict(list)
    for relationship in relationships:
        key = tuple(sorted([relationship.speaker, relationship.listener]))
        grouped_edges[key].append(relationship)

    edges = [
        RelationshipEdge(
            id=f"{source}__{target}",
            source=source,
            target=target,
            type=_edge_type(rows),
            label=_edge_label(rows),
            conflict=any(row.conflict for row in rows),
            relationships=sorted(rows, key=lambda row: (row.speaker, row.listener)),
        )
        for (source, target), rows in sorted(grouped_edges.items())
    ]
    return RelationshipCanvasResponse(
        time_key=time_key,
        timeline=_timeline_keys(project_root, cursor.volume, scope),
        nodes=nodes,
        edges=edges,
        relationships=relationships,
    )


def _relationship_update_paths(project_root: str | Path) -> list[Path]:
    paths = [_series_relationships_path(project_root)]
    db_root = resolve_project_path(project_root, "db")
    if db_root.exists():
        paths.extend(sorted(path / "relationships.json" for path in db_root.glob("volume.*") if path.is_dir()))
    return paths


def update_relationship(project_root: str | Path, relationship_id: str, request: RelationshipUpdateRequest) -> Relationship:
    updates = request.model_dump(exclude_unset=True)
    for path in _relationship_update_paths(project_root):
        if not path.exists():
            continue
        rows = read_json(path, relationship_adapter)
        for index, row in enumerate(rows):
            if row.relationship_ID != relationship_id:
                continue
            updated = row.model_copy(update=updates)
            rows[index] = updated
            write_json_atomic(path, rows, relationship_adapter, project_root=project_root, backup=True)
            return updated
    raise KeyError(f"Relationship not found: {relationship_id}")


def create_relationship(project_root: str | Path, request: RelationshipCreateRequest) -> Relationship:
    volume = request.time.volume
    characters = _characters(project_root, volume, "series")
    _validate_character_pair(characters, request.speaker, request.listener)
    record = Relationship(
        relationship_ID=allocate_id(project_root, "relationship"),
        speaker=request.speaker,
        listener=request.listener,
        type=request.type,
        relationship=request.relationship,
        pronoun=request.pronoun,
        alias_pronoun=request.alias_pronoun,
        time=request.time if request.time.key else request.time.model_copy(update={"key": request.source_segment_ID}),
        source_segment_ID=request.source_segment_ID,
        human_review=request.human_review,
        conflict=request.conflict,
        note=request.note,
    )
    rows = merge_relationship_records(_load_relationships(project_root, volume) + [record])
    write_json_atomic(
        _relationships_path(project_root, volume),
        rows,
        relationship_adapter,
        project_root=project_root,
        backup=True,
    )
    return record


def save_relationship_layout(project_root: str | Path, request: RelationshipLayoutRequest) -> dict[str, int]:
    rows = sorted(request.nodes, key=lambda node: node.id)
    write_json_atomic(_layout_path(project_root, request.volume), rows, layout_adapter, project_root=project_root, backup=True)
    return {"nodes": len(rows)}
