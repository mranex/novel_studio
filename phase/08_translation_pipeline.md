# Phase 08 - Translation Pipeline

## Goal

Dịch từng item theo batch bằng big LLM, sử dụng prompt, item text, glossary, dialogue label, và pronoun context. Kết quả lưu rất gọn: item ID + translated text.

## Inputs

- `work/volume.XX/segment_flesh.json`
- `db/volume.XX/item_glossary.json`
- `db/volume.XX/glossary.json`
- `db/volume.XX/dialogue_labels.json`
- `db/volume.XX/relationships.json`
- `prompt/translate.md`
- `prompt/json_policy.md`
- Big LLM provider config
- `settings.batch_count`

## Output

```text
db/volume.XX/translations.json
```

## Translation Schema

```json
{
  "item_ID": "v01_ch001_s001_nar_001",
  "trans_text": "Translated text"
}
```

The app may accept legacy/manual pasted `item_id` from older prompts, but it must normalize to canonical `item_ID` before saving.

Optional operational metadata can live outside source schema:

```json
{
  "item_ID": "v01_ch001_s001_nar_001",
  "status": "completed",
  "attempts": 1,
  "error": null,
  "updated_at": "ISO datetime"
}
```

Store metadata in `work/volume.XX/translation_jobs.json` if possible, keeping `db/volume.XX/translations.json` clean.

## Prompt Context Per Item

For narration:

- Translate prompt.
- JSON policy.
- Item text.
- Glossary for item.

For dialogue:

- Translate prompt.
- JSON policy.
- Item text.
- Glossary for item.
- Speaker/listener label.
- Pronoun context for speaker -> listener at item time.
- Reverse pronoun/context when available, because Vietnamese translation often needs both directions.

For dialogue items, dialogue label and pronoun context are required prompt sections. The pronoun value may be null only when no relationship/pronoun state exists yet; the section itself should still be present so the model knows the absence is intentional.

## Pronoun Context Lookup

For a dialogue item:

1. Get item segment/time.
2. Get dialogue label speaker/listener.
3. Find latest relationship record for `(speaker, listener)` where `time <= item time`.
4. Provide pronoun/type/relationship to prompt.
5. If no relationship exists, pronoun context is null.

## Batch Behavior

- User sets `batch_count`.
- App processes at most `batch_count` concurrent requests.
- Failed IDs are collected.
- User can retry failed IDs.
- User can use Prompt Studio manual mode for a single failed item.

## Retry Rules

- Retry schema failure.
- Retry provider timeout/rate limit after backoff.
- Stop after configurable attempts, default 3.
- Mark item failed with error.
- Do not overwrite completed translation unless user reruns with overwrite.

## UI Requirements

Translation page:

- Volume/chapter progress.
- Counts:
  - total items.
  - completed.
  - failed.
  - pending.
- Batch count input.
- Start/Pause/Retry Failed.
- Failed item table with error.
- Manual Prompt Studio link for item.

## API Draft

```text
POST /api/projects/{project_id}/pipeline/{volume}/translate
POST /api/projects/{project_id}/pipeline/{volume}/translate/retry-failed
GET  /api/projects/{project_id}/translations?volume=...
PATCH /api/projects/{project_id}/translations/{item_ID}
```

## Acceptance Criteria

- Translation jobs are created for every item.
- Batch count controls concurrency.
- Translation output validates schema.
- Failed jobs can retry.
- Completed translations are saved by `item_ID`.
- Dialogue translations always receive dialogue label and pronoun context sections; pronoun values can be null only when unavailable.

## Notes for Implementer

- Keep translation result minimal.
- Do not include full prompt or metadata in `db/volume.XX/translations.json`.
- Store raw provider logs separately if needed.
