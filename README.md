# Novel Translation Studio

Novel Translation Studio is an offline, single-user application for semi-automatic long-form novel translation. The project focuses on controlled translation workflow: stable text IDs, glossary management, character relationship timeline, pronoun context, dialogue labels, batch translation, human polish, and export.

This repository is currently in planning/contract stage. Implementation should begin from `phase/00_app_foundation.md`.

## Core Idea

The app is not meant to throw an entire chapter into an LLM and hope for the best.

Instead, it breaks a novel into controlled units:

1. Source volume and segment files.
2. Segment skeleton.
3. Narration/dialogue items.
4. Sub-items for glossary extraction.
5. Reviewed glossary.
6. Relationship and pronoun timeline.
7. Dialogue speaker/listener labels.
8. Item-level translation.
9. Human polish and export.

The human remains in control of glossary, relationship data, prompts, review decisions, and final translation quality.

## Main Documents

- `goal.md`  
  Explains why this project exists and what success means.

- `master_plan.md`  
  Full architecture, product scope, schemas, storage model, API draft, pipeline, and implementation phases.

- `Agent.md`  
  Rules for AI coding agents working on this project.

- `working.md`  
  Tiny index of completed work. Keep it short.

- `Working/`  
  Detailed work records from AI coding agents.

- `phase/*.md`  
  Implementation plan for each phase.

- `Novel Studio Blueprint.txt`  
  Original blueprint/reference document.

- `Dont_touch/`  
  Archived review and rebuttal documents. Do not modify unless explicitly requested.

## Planned Stack

Backend:

- Python
- FastAPI
- Pydantic
- File-based JSON/Markdown storage

Frontend:

- React
- TypeScript
- Vite
- React Flow
- Vanilla CSS + CSS Variables
- Dark mode first

Sub-app:

- Python Tkinter source preparer

LLM:

- OpenAI-compatible providers
- Small LLM for glossary extraction
- Big LLM for segmentation, relationship extraction, dialogue labeling, and translation

## Project Principles

- Offline-first.
- Single-user.
- File-based project database.
- Project folders should be shareable.
- No realtime collaboration in MVP.
- No cloud accounts or auth in MVP.
- Prompt files live in `prompt/*.md` and should be editable by the user.
- Relationship character identity must come from glossary entries, not a separate character database.
- Relationship `time` is a timestamp where a state begins, not a duration.

## Phase Order

Implementation should follow this order:

1. `phase/00_app_foundation.md`
2. `phase/01_source_preparer_sub_app.md`
3. `phase/02_project_manager_import_source.md`
4. `phase/03_skeleton_subitem_pipeline.md`
5. `phase/04_llm_provider_prompt_studio.md`
6. `phase/04a_prompt_template_design.md`
7. `phase/05_glossary_pipeline.md`
8. `phase/06_relationship_timeline_canvas.md`
9. `phase/07_dialogue_label_pipeline.md`
10. `phase/08_translation_pipeline.md`
11. `phase/08a_series_update.md`
12. `phase/09_polish_export.md`
13. `phase/10_database_editor.md`
14. `phase/11_config_packaging_polish.md`

## AI Coding Agent Workflow

Before coding, read:

1. `goal.md`
2. `master_plan.md`
3. `Agent.md`
4. `working.md`
5. Relevant `Working/*.md` notes
6. The assigned `phase/*.md`

After finishing a phase or meaningful chunk:

1. Write a detailed note in `Working/*.md`.
2. Append one short index line to root `working.md`.
3. Keep root `working.md` extremely short.

See `Agent.md` for the full rules.

## MVP Success Criteria

MVP is successful when a user can:

1. Create a project.
2. Import source volume and segment files.
3. Build skeleton, item, and sub-item data.
4. Extract, review, merge, and link glossary.
5. Extract relationship/pronoun data and view it on a timeline canvas.
6. Label dialogue speaker/listener.
7. Translate items by API or manual Prompt Studio.
8. Polish translated items.
9. Export TXT/Markdown.

## Current Status

Planning contract is complete.

Implementation has not started yet. Begin with:

```text
phase/00_app_foundation.md
```

