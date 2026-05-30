# Phase 05 - Glossary Pipeline

## Goal

Extract draft glossary bằng small LLM, merge exact duplicates, cho human review, commit glossary, link concepts, rồi scan item/segment glossary để chuẩn bị cho relationship, dialogue label, translation.

## Inputs

- `work/volume.XX/sub_items.json`
- `prompt/extract_glossary.md`
- `prompt/json_policy.md`
- Small LLM provider config
- Existing `db/series_glossary.json` for volume 2+
- `db/counters.json` for project-wide `glossary_ID` allocation

## Outputs

```text
db/volume.XX/draft_glossary.json
db/volume.XX/glossary.json
db/volume.XX/item_glossary.json
db/volume.XX/segment_glossary.json
db/series_glossary.json
```

## ID Allocation

Committed glossary IDs are project-wide, not volume-local.

Rules:

- Allocate `glossary_ID` from `db/counters.json`.
- Allocation must be atomic.
- Never reuse IDs after deletion/reject.
- If atomic counters are not reliable in the implementation environment, use UUID-style glossary IDs instead.

## Draft Glossary Schema

```json
{
  "draft_glossary_ID": "dglo_000001",
  "sub_item_ID": "v01_ch001_s001_nar_001_sub_001",
  "source": "东山",
  "type": "character"
}
```

Allowed type:

```text
character, alias, title, epithet, location, organization, weapon, artifact, magic, skill, technique, named_attack, concept, other
```

## Committed Glossary Schema

```json
{
  "glossary_ID": "glo_000001",
  "volume": 1,
  "source": "东山",
  "trans": "Đông Sơn",
  "type": "character",
  "alias": ["东山隐士"],
  "human_review": false,
  "link": [],
  "item_ID": [],
  "segment_ID": [],
  "time": {
    "volume": 1
  }
}
```

## Volume 1 Flow

1. For each sub-item, render extract glossary prompt.
2. Call small LLM or use Prompt Studio manual result.
3. Save outputs to `db/volume.XX/draft_glossary.json`.
4. Prepare merge candidates:
   - Exact source match.
   - Same type preferred.
   - Partial match ignored in MVP.
5. UI shows merge groups with `human_review = true`.
6. User approves/rejects groups.
7. Commit approved entries to `db/volume.XX/glossary.json`.
8. User can edit `trans`, `type`, `alias`, `link`.
9. Run Item Glossary Scanner.
10. Run Segment Glossary Scanner.

## Volume 2+ Flow

Before merge:

- Compare draft glossary against `series_glossary.json`.
- Exact existing source inherits series entry.
- Proper names inherit 100% unless user overrides.
- New term gets `time.volume = current volume`.

After human review:

- Mark entries as ready for series update.
- Actual write to `db/series_glossary.json` happens in `phase/08a_series_update.md` so export is not responsible for database promotion.

## Link Semantics

`link` means multiple glossary entries represent the same concept/person in context.

Rules:

- Link does not replace item glossary in translation.
- Link helps human understand pronoun/relationship editing.
- Link helps big LLM identify characters when relationship/dialogue label receives character list.
- MVP should focus link UX on character entries.

## Item Glossary Scanner

This is a separate pipeline step after glossary commit, not part of merge itself.

For each item:

1. Load item text.
2. Scan committed glossary `source` and `alias`.
3. If match, attach glossary_ID to item.
4. Store unique list.

Schema:

```json
{
  "item_ID": "v01_ch001_s001_diag_001",
  "glossary_ID": ["glo_000001", "glo_000010"]
}
```

## Segment Glossary Scanner

This is a separate pipeline step after item glossary scan.

For each segment:

1. Union all item glossary in segment.
2. Deduplicate.
3. Store.

Schema:

```json
{
  "segment_ID": "v01_ch001_s001",
  "glossary_ID": ["glo_000001", "glo_000010"]
}
```

## UI Requirements

Glossary review page:

- Table columns:
  - Source.
  - Trans.
  - Type.
  - Alias.
  - Link.
  - Found in items/segments.
  - Human review.
- Filters:
  - Type.
  - Human review.
  - Volume.
  - Missing translation.
- Actions:
  - Approve merge.
  - Reject merge.
  - Edit translation.
  - Link selected.
  - Unlink.
  - Mark ready for series update.

Basic table viewer:

- From this phase onward, provide a simple read/edit table for current volume glossary files so user can manually fix data before Phase 10 full Database Editor exists.
- Full cross-table validation and raw JSON power tools remain Phase 10 scope.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/glossary/extract
POST /api/projects/{project_id}/pipeline/{volume}/glossary/merge
POST /api/projects/{project_id}/pipeline/{volume}/glossary/scan-items
POST /api/projects/{project_id}/pipeline/{volume}/glossary/scan-segments
GET  /api/projects/{project_id}/db/volumes/{volume}/draft_glossary
GET  /api/projects/{project_id}/db/volumes/{volume}/glossary
PATCH /api/projects/{project_id}/db/volumes/{volume}/glossary/{glossary_ID}
```

## Acceptance Criteria

- Small LLM extraction can run over sub-items.
- Manual Prompt Studio path can save draft glossary.
- Exact duplicate source terms are grouped.
- Human can approve merge before commit.
- Glossary entries become source of truth for characters.
- Item glossary and segment glossary are generated by explicit scanner steps.
- Volume 2 can inherit series glossary.

## Notes for Implementer

- Do not do fuzzy partial merge in MVP.
- Do not create separate character table.
- Do not let relationship create new character IDs directly. If LLM finds unknown character, mark unresolved and let user add glossary entry.
