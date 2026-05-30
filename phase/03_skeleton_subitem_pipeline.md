# Phase 03 - Skeleton and Sub-item Pipeline

## Goal

Biến segment text thành skeleton + item flesh + sub-items. Đây là nền cho mọi bước glossary, dialogue, translation, polish.

## Inputs

- `segment/volume.XX.segment.json`
- `settings.max_subitem_tokens`

## Outputs

```text
work/volume.XX/segment_skeleton.json
work/volume.XX/segment_flesh.json
work/volume.XX/sub_items.json
```

## Item Schema

```json
{
  "item_ID": "v01_ch001_s001_nar_001",
  "segment_ID": "v01_ch001_s001",
  "chapter": "001",
  "type": "narration",
  "text": "...",
  "needs_review": false,
  "confidence": "high",
  "warnings": []
}
```

`type` values:

- `narration`
- `dialogue`

`confidence` values:

- `high`
- `low`

Naming rule: item `type` uses full words (`narration`, `dialogue`) for readability, but item IDs use short affixes (`nar`, `diag`) to match blueprint-style IDs.

## Segment Skeleton Schema

```json
{
  "segment_ID": "v01_ch001_s001",
  "items": [
    "v01_ch001_s001_nar_001",
    "v01_ch001_s001_diag_001",
    "v01_ch001_s001_nar_002"
  ]
}
```

## Sub-item Schema

```json
{
  "item_ID": "v01_ch001_s001_nar_001",
  "sub_item_ID": "v01_ch001_s001_nar_001_sub_001",
  "text": "..."
}
```

## Skeleton Builder Algorithm

For each segment:

1. Split by newline.
2. Trim each paragraph.
3. Ignore empty lines.
4. Classify paragraph:
   - Dialogue if it matches known dialogue markers/quote style.
   - Otherwise narration.
5. Assign deterministic ID by segment + type + local counter.
6. Save item order to skeleton.
7. Save item text to flesh.

## Dialogue Detection

MVP rule-based:

- Paragraph starts with quote marks common in target/source language.
- Paragraph has balanced quote markers.
- Paragraph starts with dialogue dash if source uses dash.

Dialogue marker defaults by `source_language`:

| source_language | Common markers |
|---|---|
| `zh` | `「...」`, `『...』`, `“...”`, `"..."`, `‘...’` |
| `ja` | `「...」`, `『...』`, `“...”` |
| `ko` | `"..."`, `“...”`, `‘...’` |
| `en` | `"..."`, `'...'`, em dash dialogue if configured |
| `other` | Configurable marker list |

Because source languages vary, detection must be editable later. False positives should be reviewable in Database Editor.

If a paragraph contains narration plus quoted dialogue in the same paragraph, MVP can classify the whole paragraph as `dialogue`, set `needs_review = true`, set `confidence = "low"`, and add a warning such as `mixed_narration_dialogue`. A later refinement can split mixed paragraphs more aggressively.

## Token Estimation

MVP should support two modes:

- Preferred: `tiktoken` with a stable encoding such as `cl100k_base` when available.
- Fallback: character/word heuristic:
  - CJK character approximates 1.5 tokens.
  - Latin word approximates 1.3 tokens.
  - Punctuation/whitespace adds a small buffer.

The splitter should cut before `max_subitem_tokens` with a safety margin, then move backward to the nearest sentence-ending punctuation.

## Sub-item Splitter Algorithm

For each item:

- If `type = dialogue`, do not split. Store one sub-item if glossary extraction wants it, or skip splitting and use dialogue item as sub-item.
- If `type = narration`:
  1. Estimate tokens using the configured tokenizer mode.
  2. If under max token, create one sub-item.
  3. If over max token, cut near max token but move backward to nearest sentence-ending punctuation.
  4. Continue until full text consumed.

Sub-item is only for glossary extraction. It is not used for relationship extraction, dialogue label, or translation.

## Pipeline State

Update `work/volume.XX/pipeline_state.json`:

```json
{
  "skeleton": {
    "status": "completed",
    "updated_at": "ISO datetime",
    "items": 12345
  },
  "sub_items": {
    "status": "completed",
    "updated_at": "ISO datetime",
    "sub_items": 15000
  }
}
```

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/skeleton
POST /api/projects/{project_id}/pipeline/{volume}/subitems
GET  /api/projects/{project_id}/pipeline/{volume}/items
GET  /api/projects/{project_id}/pipeline/{volume}/subitems
```

## UI Draft

Workflow page:

- Run Skeleton Builder.
- Run Sub-item Splitter.
- Show counts:
  - Segments.
  - Narration items.
  - Dialogue items.
  - Sub-items.
- Show warnings:
  - Very long dialogue.
  - Paragraph could not classify confidently.
  - Mixed narration/dialogue paragraph marked `needs_review`.

## Acceptance Criteria

- Running skeleton on imported volume creates stable item IDs.
- Running skeleton twice produces same IDs for unchanged input.
- Sub-item splitter respects max token config.
- Dialogue items are not split into multiple chunks.
- Mixed or low-confidence items carry `needs_review`, `confidence`, and `warnings`.
- Pipeline state updates correctly.
