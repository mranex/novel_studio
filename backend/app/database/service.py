from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.schemas import (
    DbRowPatchRequest,
    DbTableInfo,
    DbTableResponse,
    DbTableUpdateRequest,
    DialogueLabel,
    DraftGlossaryEntry,
    GlossaryEntry,
    ItemGlossaryEntry,
    PolishOverride,
    Relationship,
    SegmentGlossaryEntry,
    Translation,
)
from app.storage import read_json, resolve_project_path, write_json_atomic
from app.storage.helpers import volume_dir


VOLUME_TABLES: dict[str, Any] = {
    "draft_glossary": TypeAdapter(list[DraftGlossaryEntry]),
    "glossary": TypeAdapter(list[GlossaryEntry]),
    "item_glossary": TypeAdapter(list[ItemGlossaryEntry]),
    "segment_glossary": TypeAdapter(list[SegmentGlossaryEntry]),
    "relationships": TypeAdapter(list[Relationship]),
    "dialogue_labels": TypeAdapter(list[DialogueLabel]),
    "translations": TypeAdapter(list[Translation]),
    "polish_overrides": TypeAdapter(list[PolishOverride]),
}
SERIES_TABLES: dict[str, Any] = {
    "glossary": TypeAdapter(list[GlossaryEntry]),
    "relationships": TypeAdapter(list[Relationship]),
}
PRIMARY_KEYS = {
    "draft_glossary": "draft_glossary_ID",
    "glossary": "glossary_ID",
    "item_glossary": "item_ID",
    "segment_glossary": "segment_ID",
    "relationships": "relationship_ID",
    "dialogue_labels": "item_ID",
    "translations": "item_ID",
    "polish_overrides": "item_ID",
}

def _volume_path(project_root: str | Path, volume: int, table: str) -> Path:
    if table not in VOLUME_TABLES:
        raise ValueError(f"Unsupported volume table: {table}")
    return resolve_project_path(project_root, "db", volume_dir(volume), f"{table}.json")


def _series_path(project_root: str | Path, table: str) -> Path:
    if table not in SERIES_TABLES:
        raise ValueError(f"Unsupported series table: {table}")
    filename = "series_glossary.json" if table == "glossary" else "series_relationships.json"
    return resolve_project_path(project_root, "db", filename)


def _read_rows(path: Path) -> list[Any]:
    if not path.exists():
        return []
    return read_json(path, default=[])


def _validate_rows(rows: list[Any], adapter: Any) -> tuple[list[Any], list[str]]:
    try:
        validated = adapter.validate_python(rows)
        return adapter.dump_python(validated, mode="json"), _reference_errors(adapter.dump_python(validated, mode="json"))
    except ValidationError as exc:
        errors = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            errors.append(f"{location}: {error['msg']}")
        return rows, errors


def _reference_errors(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids_by_key: dict[str, set[str]] = {}
    for key in ["glossary_ID", "relationship_ID", "item_ID", "segment_ID", "draft_glossary_ID"]:
        values = [row.get(key) for row in rows if isinstance(row, dict) and row.get(key) and isinstance(row.get(key), str)]
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            errors.append(f"Duplicate {key}: {', '.join(duplicates)}")
        ids_by_key[key] = set(values)
    return errors


def list_db_tables(project_root: str | Path) -> list[DbTableInfo]:
    rows: list[DbTableInfo] = []
    db_root = resolve_project_path(project_root, "db")
    for path in sorted(db_root.glob("volume.*")) if db_root.exists() else []:
        if not path.is_dir():
            continue
        try:
            volume = int(path.name.split(".")[1])
        except (IndexError, ValueError):
            continue
        for table in VOLUME_TABLES:
            table_path = path / f"{table}.json"
            rows.append(DbTableInfo(scope="volume", name=table, volume=volume, path=str(table_path), rows=len(_read_rows(table_path))))
    for table in SERIES_TABLES:
        table_path = _series_path(project_root, table)
        rows.append(DbTableInfo(scope="series", name=table, path=str(table_path), rows=len(_read_rows(table_path))))
    return rows


def get_volume_table(project_root: str | Path, volume: int, table: str) -> DbTableResponse:
    path = _volume_path(project_root, volume, table)
    rows = _read_rows(path)
    _, errors = _validate_rows(rows, VOLUME_TABLES[table])
    return DbTableResponse(scope="volume", table=table, volume=volume, rows=rows, errors=errors)


def get_series_table(project_root: str | Path, table: str) -> DbTableResponse:
    path = _series_path(project_root, table)
    rows = _read_rows(path)
    _, errors = _validate_rows(rows, SERIES_TABLES[table])
    return DbTableResponse(scope="series", table=table, rows=rows, errors=errors)


def validate_volume_table(project_root: str | Path, volume: int, table: str, request: DbTableUpdateRequest) -> DbTableResponse:
    normalized, errors = _validate_rows(request.rows, VOLUME_TABLES[table])
    return DbTableResponse(scope="volume", table=table, volume=volume, rows=normalized, errors=errors)


def validate_series_table(project_root: str | Path, table: str, request: DbTableUpdateRequest) -> DbTableResponse:
    normalized, errors = _validate_rows(request.rows, SERIES_TABLES[table])
    return DbTableResponse(scope="series", table=table, rows=normalized, errors=errors)


def put_volume_table(project_root: str | Path, volume: int, table: str, request: DbTableUpdateRequest) -> DbTableResponse:
    response = validate_volume_table(project_root, volume, table, request)
    if response.errors:
        return response
    write_json_atomic(_volume_path(project_root, volume, table), response.rows, VOLUME_TABLES[table], project_root=project_root, backup=True)
    return get_volume_table(project_root, volume, table)


def put_series_table(project_root: str | Path, table: str, request: DbTableUpdateRequest) -> DbTableResponse:
    response = validate_series_table(project_root, table, request)
    if response.errors:
        return response
    write_json_atomic(_series_path(project_root, table), response.rows, SERIES_TABLES[table], project_root=project_root, backup=True)
    return get_series_table(project_root, table)


def patch_volume_row(project_root: str | Path, volume: int, table: str, row_id: str, request: DbRowPatchRequest) -> DbTableResponse:
    path = _volume_path(project_root, volume, table)
    rows = _read_rows(path)
    primary_key = PRIMARY_KEYS[table]
    patched = False
    next_rows = []
    for row in rows:
        if isinstance(row, dict) and row.get(primary_key) == row_id:
            merged = dict(row)
            merged.update(request.row)
            next_rows.append(merged)
            patched = True
        else:
            next_rows.append(row)
    if not patched:
        raise KeyError(f"Row not found: {row_id}")
    return put_volume_table(project_root, volume, table, DbTableUpdateRequest(rows=next_rows))
