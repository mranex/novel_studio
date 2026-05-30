from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from app.relationships.service import merge_relationship_records
from app.schemas import (
    FirstSeen,
    GlossaryEntry,
    Relationship,
    SeriesGlossaryChange,
    SeriesRelationshipChange,
    SeriesUpdatePreview,
    SeriesUpdateResponse,
    utc_now,
)
from app.storage import backup_file, resolve_project_path, write_json_atomic
from app.storage.helpers import read_json_default, volume_dir


glossary_adapter = TypeAdapter(list[GlossaryEntry])
relationship_adapter = TypeAdapter(list[Relationship])

def _volume_glossary_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "db", volume_dir(volume), "glossary.json")


def _volume_relationships_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "db", volume_dir(volume), "relationships.json")


def _series_glossary_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_glossary.json")


def _series_relationships_path(project_root: str | Path) -> Path:
    return resolve_project_path(project_root, "db", "series_relationships.json")


def _time_tuple(row: Relationship) -> tuple[int, int, int]:
    return (row.time.volume, row.time.chapter or 0, row.time.segment or 0)


def _same_relationship_state(left: Relationship, right: Relationship) -> bool:
    return (
        left.type == right.type
        and left.relationship == right.relationship
        and left.pronoun == right.pronoun
        and sorted(left.alias_pronoun) == sorted(right.alias_pronoun)
    )


def _eligible_glossary(rows: list[GlossaryEntry]) -> list[GlossaryEntry]:
    return [row for row in rows if row.human_review and row.ready_for_series_update]


def _eligible_relationships(rows: list[Relationship]) -> list[Relationship]:
    return [row for row in rows if row.human_review and row.ready_for_series_update]


def _series_glossary_record(row: GlossaryEntry, volume: int) -> GlossaryEntry:
    return row.model_copy(
        update={
            "volume": None,
            "ready_for_series_update": False,
            "first_seen": row.first_seen or FirstSeen(volume=volume),
            "last_reviewed": utc_now(),
        }
    )


def _build_next_state(project_root: str | Path, volume: int) -> tuple[SeriesUpdatePreview, list[GlossaryEntry], list[Relationship]]:
    series_glossary = read_json_default(_series_glossary_path(project_root), glossary_adapter, [])
    series_relationships = read_json_default(_series_relationships_path(project_root), relationship_adapter, [])
    volume_glossary = read_json_default(_volume_glossary_path(project_root, volume), glossary_adapter, [])
    volume_relationships = read_json_default(_volume_relationships_path(project_root, volume), relationship_adapter, [])

    glossary_by_source = {row.source: row for row in series_glossary}
    next_glossary_by_source = dict(glossary_by_source)
    preview = SeriesUpdatePreview(volume=volume)

    for row in _eligible_glossary(volume_glossary):
        promoted = _series_glossary_record(row, volume)
        existing = next_glossary_by_source.get(row.source)
        if existing is None:
            preview.glossary_changes.append(
                SeriesGlossaryChange(action="new", source=row.source, glossary_ID=promoted.glossary_ID, after=promoted)
            )
            next_glossary_by_source[row.source] = promoted
            continue
        if (
            existing.trans == row.trans
            and existing.type == row.type
            and sorted(existing.alias) == sorted(row.alias)
            and sorted(existing.link) == sorted(row.link)
        ):
            preview.glossary_changes.append(
                SeriesGlossaryChange(action="inherited", source=row.source, glossary_ID=existing.glossary_ID, before=existing, after=existing)
            )
            continue
        updated = existing.model_copy(
            update={
                "trans": row.trans,
                "type": row.type,
                "alias": row.alias,
                "link": row.link,
                "last_reviewed": utc_now(),
            }
        )
        preview.glossary_changes.append(
            SeriesGlossaryChange(action="updated", source=row.source, glossary_ID=existing.glossary_ID, before=existing, after=updated)
        )
        next_glossary_by_source[row.source] = updated

    next_relationships = list(series_relationships)
    for row in sorted(_eligible_relationships(volume_relationships), key=lambda item: (_time_tuple(item), item.relationship_ID)):
        same_pair = [candidate for candidate in next_relationships if candidate.speaker == row.speaker and candidate.listener == row.listener]
        previous = None
        for candidate in sorted(same_pair, key=lambda item: (_time_tuple(item), item.relationship_ID)):
            if _time_tuple(candidate) <= _time_tuple(row):
                previous = candidate
        if previous and _same_relationship_state(previous, row):
            preview.relationship_changes.append(
                SeriesRelationshipChange(
                    action="skipped_duplicate",
                    relationship_ID=row.relationship_ID,
                    speaker=row.speaker,
                    listener=row.listener,
                    before=previous,
                    after=row,
                )
            )
            continue
        action = "conflict" if row.conflict else "new_timestamp"
        preview.relationship_changes.append(
            SeriesRelationshipChange(
                action=action,  # type: ignore[arg-type]
                relationship_ID=row.relationship_ID,
                speaker=row.speaker,
                listener=row.listener,
                before=previous,
                after=row.model_copy(update={"ready_for_series_update": False}),
            )
        )
        next_relationships.append(row.model_copy(update={"ready_for_series_update": False}))

    preview.new_glossary_entries = sum(1 for change in preview.glossary_changes if change.action == "new")
    preview.updated_glossary_entries = sum(1 for change in preview.glossary_changes if change.action == "updated")
    preview.inherited_glossary_entries = sum(1 for change in preview.glossary_changes if change.action == "inherited")
    preview.new_relationship_timestamps = sum(1 for change in preview.relationship_changes if change.action == "new_timestamp")
    preview.skipped_duplicate_relationship_states = sum(1 for change in preview.relationship_changes if change.action == "skipped_duplicate")
    preview.conflicts_needing_review = sum(1 for change in preview.relationship_changes if change.action == "conflict")
    return (
        preview,
        sorted(next_glossary_by_source.values(), key=lambda row: (row.source.casefold(), row.glossary_ID)),
        merge_relationship_records(next_relationships),
    )


def preview_series_update(project_root: str | Path, volume: int) -> SeriesUpdatePreview:
    preview, _, _ = _build_next_state(project_root, volume)
    return preview


def apply_series_update(project_root: str | Path, volume: int) -> SeriesUpdateResponse:
    preview, glossary, relationships = _build_next_state(project_root, volume)
    backups = []
    for path in [_series_glossary_path(project_root), _series_relationships_path(project_root)]:
        backup = backup_file(path, project_root)
        if backup:
            backups.append(str(backup))
    write_json_atomic(_series_glossary_path(project_root), glossary, glossary_adapter)
    write_json_atomic(_series_relationships_path(project_root), relationships, relationship_adapter)
    return SeriesUpdateResponse(
        preview=preview,
        series_glossary_rows=len(glossary),
        series_relationship_rows=len(relationships),
        backups=backups,
    )
