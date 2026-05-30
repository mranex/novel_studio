# Phase 08a - Series Glossary and Relationship Update

## Goal

Promote reviewed volume-level glossary and relationship data into series-level files. This is a separate pipeline step, not part of export, because series data affects future volumes before translation/export happens.

## Inputs

- `db/volume.XX/glossary.json`
- `db/volume.XX/relationships.json`
- `db/series_glossary.json`
- `db/series_relationships.json`
- Human review flags from glossary and relationship workflows.

## Outputs

```text
db/series_glossary.json
db/series_relationships.json
```

## Series Glossary Rules

For each reviewed volume glossary entry:

1. If exact source already exists in series:
   - Inherit series value by default.
   - If user edited the volume entry and marks it approved, the new reviewed value can overwrite series value.
2. Proper names and character names inherit 100% by default.
3. New source term is appended with first seen volume/time metadata.
4. Linked character concepts should preserve link groups when promoted.
5. Partial/fuzzy matches are not auto-merged in MVP.

Recommended metadata:

```json
{
  "glossary_ID": "glo_000001",
  "source": "东山",
  "trans": "Đông Sơn",
  "type": "character",
  "alias": [],
  "link": [],
  "first_seen": {
    "volume": 1
  },
  "last_reviewed": "ISO datetime"
}
```

## Series Relationship Rules

Relationship remains append-only by timestamp.

For each reviewed volume relationship:

1. Find latest series relationship for the same directed pair where `time <= current time`.
2. If state is identical, inherit and do not duplicate.
3. If state changed, append the new relationship timestamp.
4. If only one part changed, keep conflict/human_review until user resolves it.
5. Null does not overwrite known pronoun/type unless user confirms.

## UI Requirements

Series Update screen:

- Show summary:
  - New glossary entries.
  - Updated glossary entries.
  - Inherited glossary entries.
  - New relationship timestamps.
  - Skipped duplicate relationship states.
  - Conflicts needing review.
- Diff panel for glossary changes.
- Diff panel for relationship changes.
- Buttons:
  - Preview Series Update.
  - Apply Series Update.
  - Cancel.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/series/preview
POST /api/projects/{project_id}/pipeline/{volume}/series/update
GET  /api/projects/{project_id}/db/series/glossary
GET  /api/projects/{project_id}/db/series/relationships
```

## Acceptance Criteria

- Series update can be previewed before write.
- Applying update creates a backup of series files first.
- Volume 2+ can inherit glossary and relationship data from series.
- Export does not mutate series files.
- New reviewed edits can override older series glossary values.

