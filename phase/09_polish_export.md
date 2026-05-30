# Phase 09 - Polish Center and Export

## Goal

Rebuild translated novel text from skeleton + translations, let user edit inline, then export to common formats.

## Inputs

- `work/volume.XX/segment_skeleton.json`
- `work/volume.XX/segment_flesh.json`
- `db/volume.XX/translations.json`
- `source/volume.XX.json`
- Optional polished overrides.

## Outputs

```text
db/volume.XX/polish_overrides.json
export/volume.01.txt
export/volume.01.md
export/volume.01.html
export/volume.01.epub
```

EPUB can be MVP-late if implementation time is tight.

## Polish Override Schema

```json
{
  "item_ID": "v01_ch001_s001_nar_001",
  "text": "User polished translated text",
  "updated_at": "ISO datetime"
}
```

If override exists, preview/export uses override instead of raw translation.

## Regeneration Algorithm

For each chapter:

1. Get all segments in chapter order.
2. For each segment, load skeleton item order.
3. For each item_ID:
   - Use polish override if exists.
   - Else use translation.
   - Else show missing marker.
4. Join items with paragraph breaks.
5. Join segments with paragraph breaks or configured separator.
6. Add chapter title.

## Polish Center UI

Layout:

- Left:
  - Volume/chapter/segment tree.
- Center:
  - Preview editor.
  - Each paragraph tied to item_ID.
- Right:
  - Item detail:
    - Original source.
    - Translation.
    - Glossary.
    - Dialogue label.
    - Pronoun context.
    - Save override.

Editing behavior:

- Inline edit text.
- Save per item.
- Show missing translations.
- Jump to failed item.

## Export Formats

TXT:

- Plain chapter title + paragraphs.

Markdown:

- `# Chapter title`
- Paragraphs.

HTML:

- Basic semantic HTML.
- No heavy styling required.

EPUB:

- Optional.
- If implemented, use generated HTML chapters and metadata.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/regenerate
GET  /api/projects/{project_id}/polish/preview?volume=...&chapter=...
PATCH /api/projects/{project_id}/polish/{item_ID}
POST /api/projects/{project_id}/export
POST /api/projects/{project_id}/export/{volume}
```

`POST /export` request body:

```json
{
  "format": "md",
  "scope": "selected_volumes",
  "volumes": [1, 2]
}
```

Supported scope values:

- `volume`: export one volume, can use `/export/{volume}`.
- `selected_volumes`: export the listed volumes in order.
- `series`: export all imported volumes in order.

## Acceptance Criteria

- App can rebuild a chapter from skeleton + translations.
- User can edit translated item inline.
- Override persists and is used in preview/export.
- Export TXT and Markdown work.
- Export supports one volume, selected volumes, or full series scope.
- Missing translations are visible, not silently dropped.

## Notes for Implementer

- Do not mutate raw translation when user polishes. Use override layer.
- Keep export deterministic.
- Do not add QA/Fix pipeline unless a later phase explicitly asks for it.
- Export must not update `series_glossary.json` or `series_relationships.json`; series promotion belongs to Phase 08a.
