# Phase 00 - App Foundation

## Goal

Dựng nền kỹ thuật tối thiểu cho app chính: backend FastAPI, frontend React, file-based project database helpers, schema validation, dev workflow. Phase này chưa cần pipeline thông minh, chỉ cần cái khung đủ chắc để các phase sau cắm vào.

## Deliverables

- Repo có backend Python FastAPI chạy được.
- Repo có frontend React + TypeScript chạy được.
- API health check.
- Shared schema definitions bằng Pydantic ở backend.
- File storage layer cho JSON/Markdown.
- Project folder abstraction.
- Dark UI shell với navigation rỗng.
- Workflow Dashboard skeleton có thể đọc `pipeline_state.json` theo volume.
- Basic tests cho storage và schema.

## Backend Tasks

- Tạo app FastAPI.
- Tạo module `schemas/`:
  - Project metadata.
  - Source volume/chapter.
  - Segment.
  - Item.
  - SubItem.
  - Glossary.
  - Relationship.
  - DialogueLabel.
  - Translation.
  - PipelineState.
  - IDCounter.
- Tạo module `storage/`:
  - Read JSON.
  - Write JSON atomic.
  - Read/write Markdown prompt.
  - Backup file trước table-level save hoặc trước pipeline run, không backup từng row write trong batch.
  - Normalize path trong project root, không cho ghi ra ngoài project.
- Tạo module `projects/`:
  - Resolve project folder.
  - Load `project.json`.
  - Load app-level settings from `~/.novel-studio/settings.json`.
  - Load project-level `settings.json` overrides.
  - Ensure folder structure.
- Tạo module `ids/`:
  - Allocate project-wide IDs from `db/counters.json`.
  - Atomic read-increment-write for counters.
  - If locking is unavailable, fallback to UUID-style IDs.
- Tạo `GET /api/health`.

## Frontend Tasks

- Tạo Vite React TypeScript app.
- Tạo app shell:
  - Left nav.
  - Top project bar.
  - Main content area.
  - Dark mode mặc định.
- Tạo route/page placeholder:
  - Project Manager.
  - Import Source.
  - Workflow.
  - Prompt Studio.
  - Database Editor.
  - Relationship Canvas.
  - Polish Center.
  - Export.
  - Config.
- Tạo API client wrapper.
- Workflow Dashboard ở Phase 00 chỉ cần đọc status và render card/list theo volume; các action button có thể disabled cho tới phase tương ứng.

## Storage Conventions

Mọi project mới phải tạo:

```text
project.json
settings.json
source/
segment/
prompt/
db/
  counters.json
  volume.01/
  series_glossary.json
  series_relationships.json
work/
export/
backups/
logs/
```

`project.json` tối thiểu:

```json
{
  "project_ID": "proj_000001",
  "name": "Novel Name",
  "genre": "xianxia",
  "source_language": "zh",
  "target_language": "vi",
  "created_at": "ISO datetime",
  "app_version": "0.1.0"
}
```

App-level `~/.novel-studio/settings.json` tối thiểu:

```json
{
  "small_llm": {
    "base_url": "http://localhost:1234/v1",
    "api_key": "",
    "model": ""
  },
  "big_llm": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": ""
  },
  "batch_count": 8,
  "theme": "dark"
}
```

Project-level `settings.json` tối thiểu:

```json
{
  "max_subitem_tokens": 1200,
  "batch_count_override": null,
  "prompt_folder": "prompt"
}
```

`db/counters.json` tối thiểu:

```json
{
  "glossary_next": 1,
  "relationship_next": 1,
  "job_next": 1
}
```

## Acceptance Criteria

- Backend starts and returns health OK.
- Frontend starts and can call health endpoint.
- Creating an empty project folder through backend creates all required folders/files.
- App-level settings and project-level overrides both load.
- Allocating `glossary_ID`/`relationship_ID` cannot duplicate IDs across volumes.
- Workflow Dashboard placeholder shows volume cards when pipeline state files exist.
- JSON write is atomic and does not corrupt existing file if validation fails.
- Basic schema tests pass.

## Notes for Implementer

- Do not overbuild auth, user accounts, plugin systems, cloud sync.
- Keep IDs deterministic where possible, but central ID allocator for glossary/relationship is fine.
- File DB should be transparent: user can open JSON manually if needed.
