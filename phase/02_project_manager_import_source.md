# Phase 02 - Project Manager and Import Source

## Goal

Cho app chính tạo/mở project, import source/segment files từ sub-app, validate, và tạo trạng thái pipeline ban đầu.

## Project Manager

Features:

- Create project.
- Open existing project folder.
- Edit basic metadata:
  - Novel name.
  - Genre.
  - Source language.
  - Target language.
  - Notes.
- Show project health:
  - Volumes imported.
  - Segments imported.
  - Pipeline status summary.

## Import Source Scene

Features:

- Import `volume.XX.json`.
- Import `volume.XX.segment.json`.
- Preview chapters and segments.
- Validate before save.
- Copy files into project `source/` and `segment/`.
- Create/update import manifest.

## Import Manifest

Create `work/import_manifest.json`:

```json
{
  "volumes": [
    {
      "volume": 1,
      "source_file": "source/volume.01.json",
      "segment_file": "segment/volume.01.segment.json",
      "chapters": 120,
      "segments": 980,
      "validated_at": "ISO datetime",
      "status": "ready"
    }
  ]
}
```

## Validation Rules

Source file:

- Root is array.
- Every entry has `chapter`, `name`, `content`.
- `chapter` unique in file.
- `content` non-empty.

Segment file:

- Root is array.
- Every entry has `chapter`, `name`, `segment`, `segment_ID`, `content`.
- `segment_ID` unique.
- `segment_ID` volume prefix matches filename `volume.XX.segment.json`; legacy IDs without prefix require explicit migration.
- `chapter` exists in source.
- `content` non-empty.
- Sort order stable.

Cross-file:

- Segment chapters must exist in source.
- Segment names should match source chapter names or show warning.
- Segment text should be plausibly contained in source chapter after whitespace normalization. If exact containment is hard, show warning not hard error.

## API Draft

```text
GET  /api/projects
POST /api/projects
POST /api/projects/open
GET  /api/projects/{project_id}
PUT  /api/projects/{project_id}/metadata

POST /api/projects/{project_id}/import/source
POST /api/projects/{project_id}/import/segment
POST /api/projects/{project_id}/import/validate
GET  /api/projects/{project_id}/import/manifest
```

## UI Draft

Project Manager:

- Project cards/list.
- Create Project modal.
- Open Folder button.
- Metadata form.

Import Source:

- Two import zones:
  - Source volume JSON.
  - Segment JSON.
- Validation results panel.
- Preview table:
  - Volume.
  - Chapter.
  - Segment count.
  - Warnings.
- Confirm Import button.

## Acceptance Criteria

- User can create a project and see required folders.
- User can import source and segment JSON.
- Invalid files do not overwrite project files.
- Import creates `db/volume.XX/` and `work/volume.XX/` folders for that volume.
- Validation errors are actionable.
- Workflow dashboard can see volume status `ready_for_skeleton`.

## Notes for Implementer

- Do not silently repair dangerous source data. Auto-generate missing `segment_ID` only if user confirms or import mode says legacy migration.
- Keep raw imported files unchanged after import. Derived normalized data belongs in `work/`.
