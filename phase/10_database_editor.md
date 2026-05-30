# Phase 10 - Database Editor

## Goal

Tạo editor tập trung để người dùng kiểm soát toàn bộ file database trong project: glossary, relationship, dialogue labels, translations, pipeline artifacts quan trọng.

## Editable Tables

MVP editable:

- `db/volume.XX/glossary.json`
- `db/volume.XX/draft_glossary.json`
- `db/volume.XX/item_glossary.json`
- `db/volume.XX/segment_glossary.json`
- `db/volume.XX/relationships.json`
- `db/volume.XX/dialogue_labels.json`
- `db/volume.XX/translations.json`
- `db/volume.XX/polish_overrides.json`
- `db/series_glossary.json`
- `db/series_relationships.json`

Read-only or advanced:

- `work/volume.XX/segment_skeleton.json`
- `work/volume.XX/segment_flesh.json`
- `work/volume.XX/sub_items.json`
- LLM raw logs.

## UI Requirements

General:

- Table selector.
- Search.
- Filter.
- Sort.
- Row detail panel.
- JSON raw view toggle.
- Validate before save.
- Save creates backup.

Glossary editor:

- Source/trans/type/alias/link.
- Character-only filter.
- Missing translation filter.
- Link selected entries.

Relationship editor:

- Speaker/listener dropdown.
- Type dropdown.
- Pronoun field.
- Time selector.
- Conflict and human review flags.
- Jump to canvas.

Dialogue label editor:

- Item_ID.
- Dialogue text preview.
- Speaker/listener dropdown.
- Human review flag.

Translation editor:

- Item_ID.
- Source preview.
- Translation field.
- Status if joined with job metadata.

## Validation

Before save:

- Schema valid.
- Required fields present.
- Reference IDs exist.
- No duplicate primary IDs.
- Relationship speaker/listener type is character.
- Dialogue item_ID is dialogue.
- Translation `item_ID` exists. Legacy `item_id` can be normalized before save.

## Backup

Every table-level save to `db/*.json` creates a timestamped backup:

```text
backups/db/volume.01/glossary.2026-05-30T10-30-00.json
```

Pipeline batch writes should create one pre-run backup per affected table, not one backup per row/request.

## API Draft

```text
GET   /api/projects/{project_id}/db/tables
GET   /api/projects/{project_id}/db/volumes/{volume}/{table}
PUT   /api/projects/{project_id}/db/volumes/{volume}/{table}
PATCH /api/projects/{project_id}/db/volumes/{volume}/{table}/{id}
POST  /api/projects/{project_id}/db/volumes/{volume}/{table}/validate
POST  /api/projects/{project_id}/db/volumes/{volume}/{table}/backup
GET   /api/projects/{project_id}/db/series/{table}
PUT   /api/projects/{project_id}/db/series/{table}
```

## Acceptance Criteria

- User can view and edit core DB tables.
- Invalid references are blocked or clearly warned.
- Save creates backup.
- Relationship and dialogue editors use glossary character dropdowns.
- Raw JSON view exists for power users.

## Notes for Implementer

- Database Editor is not a replacement for specialized UX. Glossary review, relationship canvas, and polish center can be better workflows.
- This editor is the safety hatch for advanced manual correction.
