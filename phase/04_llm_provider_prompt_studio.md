# Phase 04 - LLM Provider and Prompt Studio

## Goal

Xây hệ thống gọi LLM theo chuẩn OpenAI-compatible và Prompt Studio cho cả manual workflow lẫn API workflow.

## Provider Model

App có hai provider slot chính:

```json
{
  "small_llm": {
    "base_url": "http://localhost:1234/v1",
    "api_key": "",
    "model": "local-small-model"
  },
  "big_llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-model"
  },
  "batch_count": 8
}
```

Rules:

- Small LLM dùng cho glossary extraction.
- Big LLM dùng cho segmentation, relationship, dialogue label, translation.
- Cả hai đều dùng OpenAI-compatible request format.
- API key có thể rỗng cho local server nếu server cho phép.
- Provider defaults live in app-level `~/.novel-studio/settings.json`; project `settings.json` can override batch/token behavior without forcing API keys into a shareable project folder.

## Prompt Files

Required files:

```text
prompt/json_policy.md
prompt/segment_source.md
prompt/extract_glossary.md
prompt/extract_relationship.md
prompt/label_dialogue.md
prompt/translate.md
```

When a project is created, default prompt templates should be copied into project `prompt/`.

Default template content is specified in `phase/04a_prompt_template_design.md`. This phase implements rendering/editing/running; the 04a document defines what the shipped templates should say.

## Prompt Rendering

Prompt renderer accepts:

```json
{
  "task": "extract_glossary",
  "scope": {
    "volume": 1,
    "segment_ID": "v01_ch001_s001",
    "item_ID": null,
    "sub_item_ID": "v01_ch001_s001_nar_001_sub_001"
  }
}
```

It returns:

```json
{
  "prompt": "...rendered prompt...",
  "expected_schema": "draft_glossary",
  "provider_slot": "small_llm"
}
```

## Prompt Studio UX

Split screen:

Left side:

- Task selector:
  - Segment Source
  - Extract Glossary
  - Extract Relationship
  - Label Dialogue
  - Translate
- Scope picker.
- Prompt preview.
- Buttons:
  - Generate Prompt
  - Copy Prompt
  - Run via API

Right side:

- Result editor.
- Validation errors.
- Buttons:
  - Validate
  - Save
  - Clear

Manual mode:

1. User selects task + scope.
2. App renders prompt.
3. User copies prompt to chat.
4. User pastes result into right panel.
5. App validates JSON.
6. User clicks Save.

API mode:

1. User selects task + scope.
2. App renders prompt.
3. User clicks Run via API.
4. App fills result editor.
5. App validates.
6. User clicks Save.

Important: API mode should still require Save so user can inspect output before committing.

## LLM Job Tracking

Store in `work/volume.XX/llm_jobs.json`:

```json
{
  "job_ID": "job_000001",
  "task": "extract_glossary",
  "provider_slot": "small_llm",
  "scope": {
    "sub_item_ID": "v01_ch001_s001_nar_001_sub_001"
  },
  "status": "completed",
  "attempts": 1,
  "created_at": "ISO datetime",
  "updated_at": "ISO datetime",
  "error": null
}
```

## Validation

Each task must have:

- Expected schema.
- Validator.
- Save target.

Examples:

- Extract glossary -> `db/volume.XX/draft_glossary.json`.
- Extract relationship -> `db/volume.XX/relationships.json`.
- Label dialogue -> `db/volume.XX/dialogue_labels.json`.
- Translate -> `db/volume.XX/translations.json`.

## API Draft

```text
GET  /api/projects/{project_id}/prompts
GET  /api/projects/{project_id}/prompts/{name}
PUT  /api/projects/{project_id}/prompts/{name}
POST /api/projects/{project_id}/prompts/render
POST /api/projects/{project_id}/llm/run
POST /api/projects/{project_id}/prompts/validate-result
POST /api/projects/{project_id}/prompts/save-result
```

## Acceptance Criteria

- User can edit prompt files from UI.
- User can render prompt for a selected scope.
- User can copy prompt manually.
- User can run via configured API.
- Result validation catches invalid JSON/schema.
- Save writes to correct local DB file.

## Notes for Implementer

- Do not hardcode provider-specific APIs beyond OpenAI-compatible.
- Structured output support can be added when provider supports it, but manual paste validator still needed.
- Keep raw LLM output logs for debugging, but do not let logs become source of truth.
