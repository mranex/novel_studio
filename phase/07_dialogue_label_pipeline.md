# Phase 07 - Dialogue Label Pipeline

## Goal

Label dialogue items with speaker/listener using big LLM, without depending on relationship data.

## Inputs

- Segment text.
- Segment items from `work/volume.XX/segment_flesh.json`.
- Segment glossary character list from `db/volume.XX/segment_glossary.json` + `db/volume.XX/glossary.json` + inherited series character entries where applicable.
- `prompt/label_dialogue.md`.
- `prompt/json_policy.md`.
- Big LLM provider config.

## Output

```text
db/volume.XX/dialogue_labels.json
```

## Schema

```json
{
  "item_ID": "v01_ch001_s001_diag_001",
  "speaker": "glo_000007",
  "listener": "glo_000010",
  "human_review": false,
  "confidence": null,
  "note": ""
}
```

`speaker` and `listener` can be null if unclear.

## Flow

For each segment:

1. Prepare segment text.
2. Prepare dialogue item IDs and text.
3. Prepare character glossary list.
4. Render label dialogue prompt.
5. Big LLM returns item_ID -> speaker/listener.
6. Validate:
   - item_ID exists.
   - item type is dialogue.
   - speaker/listener are character glossary_ID or null.
7. Save labels.
8. Mark uncertain/null labels as `human_review = true`.

## Why Relationship Is Not Required

Dialogue labeling answers "who speaks to whom in this segment". Relationship answers "what is their relationship/pronoun state over time". They should not be coupled, because relationship data may be missing, wrong, or extracted later.

Translation can later combine dialogue label + relationship/pronoun state.

## UI Requirements

Dialogue Label Review:

- Segment selector.
- Dialogue list.
- Each row:
  - item_ID.
  - dialogue text.
  - speaker dropdown.
  - listener dropdown.
  - human_review checkbox.
- Character dropdown should show:
  - trans.
  - source.
  - alias.
  - linked entries.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/dialogue-labels/extract
GET  /api/projects/{project_id}/dialogue-labels?segment_ID=...
PATCH /api/projects/{project_id}/dialogue-labels/{item_ID}
```

## Acceptance Criteria

- Dialogue label extraction works per segment.
- Output never includes full dialogue text, only IDs and speaker/listener.
- Unknown speaker/listener can be null.
- Null/uncertain labels appear in review UI.
- User edits are saved to `db/volume.XX/dialogue_labels.json`.

## Notes for Implementer

- Keep this pipeline independent from relationship extraction.
- Do not let LLM invent character IDs. Unknown character should be null or unresolved.
