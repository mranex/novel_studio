from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from pydantic import TypeAdapter

from app.ids import allocate_id
from app.llm import call_llm
from app.pipeline import load_items, load_subitems
from app.pipeline.state import set_pipeline_step
from app.prompts.service import render_prompt, validate_prompt_result
from app.projects import ensure_app_settings
from app.schemas import (
    DraftGlossaryEntry,
    GlossaryEntry,
    GlossaryMergeGroup,
    GlossaryMergeRequest,
    GlossaryMergeResponse,
    GlossaryTableResponse,
    GlossaryType,
    GlossaryUpdateRequest,
    ItemGlossaryEntry,
    PipelineRunResponse,
    PromptRenderRequest,
    PromptResultRequest,
    PromptScope,
    SegmentGlossaryEntry,
    TimelinePoint,
)
from app.storage import resolve_project_path, write_json_atomic
from app.storage.helpers import db_volume_dir, read_json_default, work_volume_dir


draft_adapter = TypeAdapter(list[DraftGlossaryEntry])
glossary_adapter = TypeAdapter(list[GlossaryEntry])
item_glossary_adapter = TypeAdapter(list[ItemGlossaryEntry])
segment_glossary_adapter = TypeAdapter(list[SegmentGlossaryEntry])

def _db_dir(project_root: str | Path, volume: int) -> Path:
    return db_volume_dir(project_root, volume)


def _work_dir(project_root: str | Path, volume: int) -> Path:
    return work_volume_dir(project_root, volume)


def _draft_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "draft_glossary.json"


def _glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "glossary.json"


def _item_glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "item_glossary.json"


def _segment_glossary_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "segment_glossary.json"


def _series_glossary_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_glossary.json")


def _load_drafts(project_root: str | Path, volume: int) -> list[DraftGlossaryEntry]:
    return read_json_default(_draft_path(project_root, volume), draft_adapter, [])


def _load_glossary(project_root: str | Path, volume: int) -> list[GlossaryEntry]:
    return read_json_default(_glossary_path(project_root, volume), glossary_adapter, [])


def _load_series_glossary(project_root: str | Path) -> list[GlossaryEntry]:
    return read_json_default(_series_glossary_path(project_root), glossary_adapter, [])


def _draft_id(existing_count: int, offset: int) -> str:
    return f"dglo_{existing_count + offset:06d}"


def extract_draft_glossary(project_root: str | Path, volume: int) -> PipelineRunResponse:
    subitems = load_subitems(project_root, volume)
    existing = _load_drafts(project_root, volume)
    existing_keys = {(row.sub_item_ID, row.source, row.type) for row in existing}
    new_rows: list[DraftGlossaryEntry] = []
    settings = ensure_app_settings()

    for subitem in subitems:
        render = render_prompt(
            project_root,
            PromptRenderRequest(
                task="extract_glossary",
                scope=PromptScope(volume=volume, sub_item_ID=subitem.sub_item_ID),
            ),
        )
        raw_result = call_llm(settings, render.provider_slot, render.prompt)
        result_path = _work_dir(project_root, volume) / "llm_results" / f"extract_glossary_{subitem.sub_item_ID}.txt"
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(raw_result, encoding="utf-8")

        validation = validate_prompt_result(
            project_root,
            PromptResultRequest(
                task="extract_glossary",
                scope=PromptScope(volume=volume, sub_item_ID=subitem.sub_item_ID),
                result_text=raw_result,
            ),
        )
        if not validation.ok:
            raise ValueError("; ".join(validation.errors))
        rows = draft_adapter.validate_python(validation.normalized or [])
        for row in rows:
            key = (row.sub_item_ID, row.source, row.type)
            if key in existing_keys:
                continue
            new_rows.append(
                DraftGlossaryEntry(
                    draft_glossary_ID=row.draft_glossary_ID or _draft_id(len(existing), len(new_rows) + 1),
                    sub_item_ID=row.sub_item_ID,
                    source=row.source,
                    type=row.type,
                )
            )
            existing_keys.add(key)

    all_rows = existing + new_rows
    write_json_atomic(_draft_path(project_root, volume), all_rows, draft_adapter, project_root=project_root, backup=True)
    state = set_pipeline_step(
        project_root,
        volume,
        "glossary_extract",
        "needs_review",
        f"{len(new_rows)} draft glossary rows extracted",
        {"draft_rows": len(all_rows), "new_rows": len(new_rows)},
    )
    return PipelineRunResponse(
        volume=volume,
        pipeline_state=state,
        counts={"draft_rows": len(all_rows), "new_rows": len(new_rows)},
        warnings=[],
    )


def _group_key(source: str, type_value: str) -> str:
    return f"{type_value}::{source}"


def _build_merge_groups(project_root: str | Path, volume: int, drafts: list[DraftGlossaryEntry]) -> list[GlossaryMergeGroup]:
    series_by_source = {entry.source: entry for entry in _load_series_glossary(project_root)}
    grouped: dict[tuple[str, GlossaryType], list[DraftGlossaryEntry]] = defaultdict(list)
    for draft in drafts:
        grouped[(draft.source, draft.type)].append(draft)

    groups: list[GlossaryMergeGroup] = []
    for (source, type_value), rows in sorted(grouped.items(), key=lambda item: (item[0][0].casefold(), item[0][1])):
        inherited = series_by_source.get(source) if volume > 1 else None
        groups.append(
            GlossaryMergeGroup(
                group_key=_group_key(source, type_value),
                source=source,
                type=type_value,
                draft_glossary_ID=[row.draft_glossary_ID or "" for row in rows if row.draft_glossary_ID],
                sub_item_ID=sorted({row.sub_item_ID for row in rows}),
                count=len(rows),
                inherited_glossary_ID=inherited.glossary_ID if inherited else None,
                suggested_trans=inherited.trans if inherited else "",
            )
        )
    return groups


def _source_segments_for_items(project_root: str | Path, volume: int, item_ids: list[str]) -> list[str]:
    item_by_id = {item.item_ID: item for item in load_items(project_root, volume)}
    return sorted({item_by_id[item_id].segment_ID for item_id in item_ids if item_id in item_by_id})


def merge_draft_glossary(project_root: str | Path, volume: int, request: GlossaryMergeRequest | None = None) -> GlossaryMergeResponse:
    request = request or GlossaryMergeRequest()
    drafts = _load_drafts(project_root, volume)
    groups = _build_merge_groups(project_root, volume, drafts)
    approved = set(request.approved_group_keys)
    rejected = set(request.rejected_group_keys)
    existing = _load_glossary(project_root, volume)
    existing_sources = {(entry.source, entry.type) for entry in existing}
    created: list[GlossaryEntry] = []

    subitems = {sub.sub_item_ID: sub for sub in load_subitems(project_root, volume)}
    source_to_items: dict[str, set[str]] = defaultdict(set)
    for draft in drafts:
        subitem = subitems.get(draft.sub_item_ID)
        if subitem:
            source_to_items[_group_key(draft.source, draft.type)].add(subitem.item_ID)

    for group in groups:
        group.approved = group.group_key in approved
        group.rejected = group.group_key in rejected
        if not group.approved or (group.source, group.type) in existing_sources:
            continue
        item_ids = sorted(source_to_items.get(group.group_key, set()))
        created.append(
            GlossaryEntry(
                glossary_ID=allocate_id(project_root, "glossary"),
                volume=volume,
                source=group.source,
                trans=group.suggested_trans,
                type=group.type,
                alias=[],
                human_review=True,
                link=[group.inherited_glossary_ID] if group.inherited_glossary_ID else [],
                item_ID=item_ids,
                segment_ID=_source_segments_for_items(project_root, volume, item_ids),
                time=TimelinePoint(volume=volume),
            )
        )
        existing_sources.add((group.source, group.type))

    glossary = existing + created
    if created:
        write_json_atomic(_glossary_path(project_root, volume), glossary, glossary_adapter, project_root=project_root, backup=True)
    state = set_pipeline_step(
        project_root,
        volume,
        "glossary_merge",
        "needs_review" if groups else "not_started",
        f"{len(created)} glossary entries committed",
        {"groups": len(groups), "created": len(created), "glossary_rows": len(glossary)},
    )
    return GlossaryMergeResponse(volume=volume, groups=groups, created=created, glossary=glossary)


def _entry_terms(entry: GlossaryEntry) -> list[str]:
    return [term for term in [entry.source, *entry.alias] if term]


def scan_item_glossary(project_root: str | Path, volume: int) -> PipelineRunResponse:
    glossary = _load_glossary(project_root, volume)
    rows: list[ItemGlossaryEntry] = []
    matched_segments: dict[str, set[str]] = defaultdict(set)
    matched_items: dict[str, set[str]] = defaultdict(set)

    for item in load_items(project_root, volume):
        matches = []
        for entry in glossary:
            if any(term and term in item.text for term in _entry_terms(entry)):
                matches.append(entry.glossary_ID)
                matched_items[entry.glossary_ID].add(item.item_ID)
                matched_segments[entry.glossary_ID].add(item.segment_ID)
        rows.append(ItemGlossaryEntry(item_ID=item.item_ID, glossary_ID=sorted(set(matches))))

    for entry in glossary:
        entry.item_ID = sorted(set(entry.item_ID) | matched_items.get(entry.glossary_ID, set()))
        entry.segment_ID = sorted(set(entry.segment_ID) | matched_segments.get(entry.glossary_ID, set()))

    write_json_atomic(_item_glossary_path(project_root, volume), rows, item_glossary_adapter, project_root=project_root, backup=True)
    write_json_atomic(_glossary_path(project_root, volume), glossary, glossary_adapter, project_root=project_root, backup=True)
    metrics = {"items": len(rows), "matched_items": sum(1 for row in rows if row.glossary_ID)}
    state = set_pipeline_step(
        project_root,
        volume,
        "glossary_scan_items",
        "completed",
        f"{sum(1 for row in rows if row.glossary_ID)} items matched glossary",
        metrics,
    )
    return PipelineRunResponse(volume=volume, pipeline_state=state, counts=metrics, warnings=[])


def scan_segment_glossary(project_root: str | Path, volume: int) -> PipelineRunResponse:
    item_rows = read_json_default(_item_glossary_path(project_root, volume), item_glossary_adapter, [])
    items = {item.item_ID: item for item in load_items(project_root, volume)}
    segment_map: dict[str, set[str]] = defaultdict(set)
    for row in item_rows:
        item = items.get(row.item_ID)
        if item:
            segment_map[item.segment_ID].update(row.glossary_ID)

    segment_rows = [
        SegmentGlossaryEntry(segment_ID=segment_id, glossary_ID=sorted(glossary_ids))
        for segment_id, glossary_ids in sorted(segment_map.items())
    ]
    write_json_atomic(
        _segment_glossary_path(project_root, volume),
        segment_rows,
        segment_glossary_adapter,
        project_root=project_root,
        backup=True,
    )
    metrics = {"segments": len(segment_rows)}
    state = set_pipeline_step(
        project_root,
        volume,
        "glossary_scan_segments",
        "completed",
        f"{len(segment_rows)} segments scanned",
        metrics,
    )
    return PipelineRunResponse(volume=volume, pipeline_state=state, counts=metrics, warnings=[])


def get_volume_table(project_root: str | Path, volume: int, table: str) -> GlossaryTableResponse:
    adapters = {
        "draft_glossary": (draft_adapter, _draft_path(project_root, volume)),
        "glossary": (glossary_adapter, _glossary_path(project_root, volume)),
        "item_glossary": (item_glossary_adapter, _item_glossary_path(project_root, volume)),
        "segment_glossary": (segment_glossary_adapter, _segment_glossary_path(project_root, volume)),
    }
    if table not in adapters:
        raise ValueError(f"Unsupported volume table: {table}")
    adapter, path = adapters[table]
    rows = read_json_default(path, adapter, [])
    return GlossaryTableResponse(table=table, volume=volume, rows=adapter.dump_python(rows, mode="json"))


def update_glossary_entry(
    project_root: str | Path,
    volume: int,
    glossary_id: str,
    request: GlossaryUpdateRequest,
) -> GlossaryEntry:
    glossary = _load_glossary(project_root, volume)
    for index, entry in enumerate(glossary):
        if entry.glossary_ID != glossary_id:
            continue
        updates = request.model_dump(exclude_unset=True)
        updated = entry.model_copy(update=updates)
        glossary[index] = updated
        write_json_atomic(_glossary_path(project_root, volume), glossary, glossary_adapter, project_root=project_root, backup=True)
        return updated
    raise KeyError(f"Glossary entry not found: {glossary_id}")
