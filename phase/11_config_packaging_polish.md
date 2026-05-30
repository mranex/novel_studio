# Phase 11 - Config, Packaging, and MVP Polish

## Goal

Hoàn thiện config, local/offline ergonomics, dark UI polish, packaging/dev run instructions, và những guardrails cần thiết để app dùng được ổn định.

## Config Scene

Fields:

App-level fields in `~/.novel-studio/settings.json`:

- Small LLM:
  - Base URL.
  - API key.
  - Model.
  - Test connection.
- Big LLM:
  - Base URL.
  - API key.
  - Model.
  - Test connection.
- Batch:
  - Batch count input.
- Theme:
  - Dark mode default.
  - Light mode optional/later.

Project-level fields in project `settings.json`:

- Processing:
  - Max sub-item tokens.
- Prompt:
  - Project prompt folder.
- Optional overrides:
  - Batch count override.

## Batch Config

User only needs to set one number:

```json
{
  "batch_count": 8
}
```

Implementation can internally map this to concurrency. Do not expose complex queue controls in MVP unless needed.

## Offline Behavior

- App can open existing project without internet.
- Local LM Studio server can be used with empty API key.
- If provider unavailable, UI should fail gracefully.
- Manual Prompt Studio mode remains usable even without API.

## Security Notes

- MVP can store API key locally in app-level `~/.novel-studio/settings.json`.
- UI should warn before storing API keys in a project folder because project folders are meant to be shareable.
- Later enhancement: OS keychain.

## Packaging Options

MVP dev mode:

- Backend runs with Uvicorn.
- Frontend runs with Vite.

Later packaging:

- Desktop wrapper optional.
- Single launch script optional.
- PyInstaller for sub-app optional.

## UI Polish Rules

- UI language: English.
- Dark mode primary.
- Dense, work-focused interface.
- Avoid marketing/landing page.
- Use real controls:
  - Dropdowns for task/type.
  - Sliders for timeline.
  - Tables for DB.
  - Buttons with icons where frontend stack supports it.
- Do not put huge hero sections in operational screens.
- Relationship canvas should be full workspace, not tiny decorative preview.

## Logging

Store logs under:

```text
logs/
```

Recommended logs:

- Import validation.
- Pipeline runs.
- LLM job errors.
- Export runs.

Do not store API key in logs.

## Test Checklist

Before MVP handoff:

- Create project.
- Import sample volume and segments.
- Run skeleton/sub-items.
- Extract glossary via manual Prompt Studio mock result.
- Merge glossary.
- Create relationship manually and verify timeline persistence.
- Label dialogue manually.
- Translate at least one item manually/API.
- Polish and export TXT/MD.
- Reopen project and verify data persists.

## Acceptance Criteria

- Config UI can test small/big providers.
- Batch count is saved and used by translation pipeline.
- Manual mode works without provider.
- App has coherent dark theme.
- Basic run instructions exist.
- Sample end-to-end project path works.

## Notes for Implementer

- Polish should make the app feel reliable, not flashy.
- Keep offline single-user assumption everywhere.
- Do not add collaboration or cloud features in this phase.
