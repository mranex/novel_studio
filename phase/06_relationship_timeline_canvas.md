# Phase 06 - Relationship Timeline and Canvas

## Goal

Extract relationship/pronoun bằng big LLM, merge duplicate relationship states, quản lý conflict, và render relationship canvas bằng React Flow với timeline slider.

## Inputs

- Segment text from `segment/volume.XX.segment.json`
- Segment glossary from `db/volume.XX/segment_glossary.json`
- Character glossary entries from `db/volume.XX/glossary.json` plus inherited series glossary where applicable
- `prompt/extract_relationship.md`
- `prompt/json_policy.md`
- Big LLM provider config
- Existing `db/series_relationships.json` for volume 2+
- `db/counters.json` for project-wide `relationship_ID` allocation

## Output

```text
db/volume.XX/relationships.json
db/series_relationships.json
```

## ID Allocation

Relationship IDs are project-wide.

- Allocate `relationship_ID` from `db/counters.json`.
- Allocation must be atomic.
- Never reuse IDs after deletion/reject.
- UUID-style IDs are acceptable if atomic counters are unavailable.

## Relationship Schema

```json
{
  "relationship_ID": "rel_000001",
  "speaker": "glo_000007",
  "listener": "glo_000010",
  "type": "ally",
  "relationship": "teacher/student",
  "pronoun": "lão phu",
  "alias_pronoun": [],
  "time": {
    "volume": 1,
    "chapter": 1,
    "segment": 7,
    "key": "v01_ch001_s007"
  },
  "source_segment_ID": "v01_ch001_s007",
  "human_review": false,
  "conflict": false,
  "note": ""
}
```

Allowed `type`:

```text
ally, enemy, neutral, unknown, love, family
```

## Extraction Flow

For each segment:

1. Prepare character list from segment glossary:
   - glossary_ID.
   - source.
   - alias.
   - link group if available.
2. Render prompt.
3. Big LLM returns directed relationships:
   - speaker.
   - listener.
   - type.
   - relationship.
   - pronoun.
   - time.
4. Validate speaker/listener are valid character glossary_ID.
5. Save raw accepted relationship records.
6. Run merge/conflict pass.

## Time Semantics

`time` is the first point where a relationship state becomes true. It persists until a newer state for the same directed pair appears.

Render algorithm:

1. User cursor = volume/chapter/segment.
2. Backend aggregates relationship records from `db/series_relationships.json` plus every imported `db/volume.XX/relationships.json` up to the cursor volume.
3. For each directed pair `(speaker, listener)`, find latest relationship where `time <= cursor`.
4. Canvas edge between two nodes uses combined summary of both directions.
5. Detail panel shows directed records separately.

Canvas scope:

- Default scope is the whole imported series up to the selected cursor, not only the active volume.
- UI may offer an `active volume only` debug/filter mode, but the main timeline should behave as series-wide continuity.

Example:

- `v01_ch001_s007`: A -> B ally, pronoun "lão phu".
- No later record.
- Cursor at chapter 100 still shows this state.

If `v01_ch010_s003` says A -> B enemy, cursor after that shows enemy.

## Merge Rules

Compare new record against previous latest record of same directed pair.

- Full duplicate:
  - Same type.
  - Same relationship.
  - Same pronoun.
  - Same alias_pronoun.
  - Action: discard new duplicate or mark as merged reference.

- Partial duplicate/conflict:
  - Type same but pronoun changed.
  - Pronoun same but type changed.
  - Relationship text changed but type same.
  - Action: keep new record with `conflict = true`, `human_review = true`.

- Clear change:
  - Type and pronoun/relationship changed.
  - Action: keep as new timestamp state.

- Null handling:
  - Null does not overwrite known value automatically.
  - Null output should be accepted but marked as unknown or needs review depending on context.

## Canvas Requirements

React Flow:

- Node = glossary entry with `type = character`.
- Edge = any relationship between two characters at selected time.
- Node label:
  - `trans` if exists.
  - fallback `source`.
- Edge color:
  - ally: green.
  - enemy: red.
  - neutral: yellow.
  - unknown: gray.
  - love: pink.
  - family: blue.
- Edge detail:
  - Relationship type.
  - Pronouns both directions if available.
  - Timestamp.
  - Source segment.
  - Conflict marker.

Timeline:

- Slider at bottom.
- Tick labels by chapter, optional segment granularity.
- Cursor state shown as `Volume 1 / Chapter 3 / Segment 2`.
- When user moves slider, canvas recomputes state.

Editing:

- Drag nodes.
- Edit relationship in side panel.
- Add relationship manually between two character nodes.
- Mark conflict resolved.
- Save layout positions separately from relationship data.

Layout file:

```text
work/volume.XX/relationship_canvas_layout.json
```

## Series Relationship Flow

For volume 2+:

- Load series relationships as prior state.
- If current volume extracts same state, inherit existing and do not duplicate.
- If current volume changes state, append new timestamp.
- Human review before marking records ready for series update.
- Actual write to `db/series_relationships.json` happens in `phase/08a_series_update.md`.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/relationships/extract
POST /api/projects/{project_id}/pipeline/{volume}/relationships/merge
GET  /api/projects/{project_id}/relationships/state?time_key=...&scope=series
GET  /api/projects/{project_id}/relationships/canvas?time_key=...&scope=series
PATCH /api/projects/{project_id}/relationships/{relationship_ID}
POST /api/projects/{project_id}/relationships
PUT  /api/projects/{project_id}/relationships/layout
```

## Acceptance Criteria

- Relationship extraction accepts only glossary character IDs.
- Duplicate state does not spam later chapters.
- State persists when timeline moves forward.
- Canvas state aggregates relationships across imported volumes by default.
- New timestamp changes rendered canvas after that time.
- Conflict records are visible and editable.
- React Flow canvas renders nodes/edges and timeline slider updates graph.

## Notes for Implementer

- Canvas is visualization/editing layer, not separate identity database.
- Relationship data remains append-only event/state records.
- Do not build complex graph analytics in MVP.
