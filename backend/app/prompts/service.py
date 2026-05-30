from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.ids import allocate_id
from app.llm import call_llm
from app.projects import ensure_app_settings, load_project_metadata, load_project_settings
from app.prompts.defaults import DEFAULT_PROMPTS
from app.schemas import (
    DialogueLabel,
    DraftGlossaryEntry,
    LLMJob,
    LLMRunRequest,
    LLMRunResponse,
    PipelineItem,
    PipelineSubItem,
    PromptRelationshipResult,
    PromptFileInfo,
    PromptRenderRequest,
    PromptRenderResponse,
    PromptResultRequest,
    PromptSaveResponse,
    PromptTask,
    PromptTranslationResult,
    PromptValidationResponse,
    Relationship,
    SourceChapter,
    SourceSegment,
    SourceSegmentDraft,
    TimelinePoint,
    Translation,
    utc_now,
)
from app.storage import read_json, read_markdown, resolve_project_path, write_json_atomic, write_markdown_atomic
from app.storage.helpers import read_json_default, volume_dir


TASK_CONFIG: dict[PromptTask, dict[str, str]] = {
    "segment_source": {
        "template": "segment_source.md",
        "expected_schema": "source_segments",
        "provider_slot": "big_llm",
    },
    "extract_glossary": {
        "template": "extract_glossary.md",
        "expected_schema": "draft_glossary",
        "provider_slot": "small_llm",
    },
    "extract_relationship": {
        "template": "extract_relationship.md",
        "expected_schema": "relationships",
        "provider_slot": "big_llm",
    },
    "label_dialogue": {
        "template": "label_dialogue.md",
        "expected_schema": "dialogue_labels",
        "provider_slot": "big_llm",
    },
    "translate": {
        "template": "translate.md",
        "expected_schema": "translation",
        "provider_slot": "big_llm",
    },
}

PROMPT_FILE_NAMES = list(DEFAULT_PROMPTS.keys())
draft_glossary_adapter = TypeAdapter(list[DraftGlossaryEntry])
relationship_result_adapter = TypeAdapter(list[PromptRelationshipResult])
relationship_adapter = TypeAdapter(list[Relationship])
dialogue_label_adapter = TypeAdapter(list[DialogueLabel])
source_segment_draft_adapter = TypeAdapter(list[SourceSegmentDraft])
translation_adapter = TypeAdapter(list[Translation])
translation_result_adapter = TypeAdapter(PromptTranslationResult)
llm_job_adapter = TypeAdapter(list[LLMJob])
TIME_KEY_RE = re.compile(r"^v(?P<volume>\d+)_ch(?P<chapter>\d+)_s(?P<segment>\d+)$")


def ensure_prompt_files(project_root: str | Path) -> None:
    prompt_root = resolve_project_path(project_root, "prompt")
    prompt_root.mkdir(parents=True, exist_ok=True)
    for name, content in DEFAULT_PROMPTS.items():
        path = prompt_root / name
        if not path.exists():
            write_markdown_atomic(path, content)


def list_prompt_files(project_root: str | Path) -> list[PromptFileInfo]:
    ensure_prompt_files(project_root)
    prompt_root = resolve_project_path(project_root, "prompt")
    files = []
    for path in sorted(prompt_root.glob("*.md")):
        files.append(PromptFileInfo(name=path.name, path=str(path)))
    return files


def _prompt_path(project_root: str | Path, name: str) -> Path:
    if name not in PROMPT_FILE_NAMES:
        raise ValueError(f"Unknown prompt file: {name}")
    ensure_prompt_files(project_root)
    return resolve_project_path(project_root, "prompt", name)


def read_prompt_file(project_root: str | Path, name: str) -> str:
    return read_markdown(_prompt_path(project_root, name))


def update_prompt_file(project_root: str | Path, name: str, content: str) -> str:
    path = _prompt_path(project_root, name)
    write_markdown_atomic(path, content, project_root=project_root, backup=True)
    return read_markdown(path)

def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _find_segment(project_root: str | Path, volume: int, segment_id: str | None) -> SourceSegment | None:
    if not segment_id:
        return None
    path = resolve_project_path(project_root, "segment", f"volume.{volume:02d}.segment.json")
    segments = read_json(path)
    for item in segments:
        if item.get("segment_ID") == segment_id:
            return SourceSegment.model_validate(item)
    return None


def _find_chapter(project_root: str | Path, volume: int, chapter: str | None) -> SourceChapter | None:
    if not chapter:
        return None
    path = resolve_project_path(project_root, "source", f"volume.{volume:02d}.json")
    chapters = read_json(path)
    for item in chapters:
        if item.get("chapter") == chapter:
            return SourceChapter.model_validate(item)
    return None


def _find_item(project_root: str | Path, volume: int, item_id: str | None) -> PipelineItem | None:
    if not item_id:
        return None
    path = resolve_project_path(project_root, "work", volume_dir(volume), "segment_flesh.json")
    items = read_json(path)
    for item in items:
        if item.get("item_ID") == item_id:
            return PipelineItem.model_validate(item)
    return None


def _find_subitem(project_root: str | Path, volume: int, sub_item_id: str | None) -> PipelineSubItem | None:
    if not sub_item_id:
        return None
    path = resolve_project_path(project_root, "work", volume_dir(volume), "sub_items.json")
    subitems = read_json(path)
    for item in subitems:
        if item.get("sub_item_ID") == sub_item_id:
            return PipelineSubItem.model_validate(item)
    return None


def _segment_items(project_root: str | Path, volume: int, segment_id: str | None) -> list[dict[str, Any]]:
    path = resolve_project_path(project_root, "work", volume_dir(volume), "segment_flesh.json")
    if not path.exists() or not segment_id:
        return []
    items = read_json(path)
    return [
        {
            "item_ID": item.get("item_ID"),
            "type": item.get("type"),
            "text": item.get("text"),
        }
        for item in items
        if item.get("segment_ID") == segment_id
    ]


def _segment_characters(project_root: str | Path, volume: int, segment_id: str | None) -> list[dict[str, Any]]:
    volume_db = resolve_project_path(project_root, "db", volume_dir(volume))
    glossary_ids: set[str] = set()
    segment_path = volume_db / "segment_glossary.json"
    if segment_path.exists() and segment_id:
        for row in read_json(segment_path):
            if row.get("segment_ID") == segment_id:
                glossary_ids.update(row.get("glossary_ID") or [])

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in [resolve_project_path(project_root, "db", "series_glossary.json"), volume_db / "glossary.json"]:
        if not path.exists():
            continue
        for row in read_json(path):
            if row.get("type") != "character":
                continue
            glossary_id = row.get("glossary_ID")
            linked_ids = set(row.get("link") or [])
            if glossary_ids and glossary_id not in glossary_ids and glossary_ids.isdisjoint(linked_ids):
                continue
            if glossary_id in seen:
                continue
            seen.add(glossary_id)
            candidates.append(
                {
                    "glossary_ID": glossary_id,
                    "source": row.get("source", ""),
                    "trans": row.get("trans", ""),
                    "alias": row.get("alias", []),
                    "link": row.get("link", []),
                }
            )
    return candidates


def _dialogue_label(project_root: str | Path, volume: int, item_id: str | None) -> dict[str, Any] | None:
    path = resolve_project_path(project_root, "db", volume_dir(volume), "dialogue_labels.json")
    if not path.exists() or not item_id:
        return None
    for row in read_json(path):
        if row.get("item_ID") == item_id:
            return row
    return None


def _item_glossary(project_root: str | Path, volume: int, item_id: str | None) -> list[dict[str, Any]]:
    if not item_id:
        return []
    volume_db = resolve_project_path(project_root, "db", volume_dir(volume))
    item_glossary_path = volume_db / "item_glossary.json"
    if not item_glossary_path.exists():
        return []
    glossary_ids: set[str] = set()
    for row in read_json(item_glossary_path, default=[]):
        if row.get("item_ID") == item_id:
            glossary_ids.update(row.get("glossary_ID") or [])
            break
    if not glossary_ids:
        return []

    entries: dict[str, dict[str, Any]] = {}
    for path in [resolve_project_path(project_root, "db", "series_glossary.json"), volume_db / "glossary.json"]:
        if not path.exists():
            continue
        for row in read_json(path, default=[]):
            glossary_id = row.get("glossary_ID")
            if glossary_id in glossary_ids:
                entries[glossary_id] = {
                    "glossary_ID": glossary_id,
                    "source": row.get("source", ""),
                    "trans": row.get("trans", ""),
                    "type": row.get("type", ""),
                    "alias": row.get("alias", []),
                }
    return [entries[key] for key in sorted(entries)]


def _time_tuple_from_point(time: dict[str, Any] | None) -> tuple[int, int, int]:
    if not isinstance(time, dict):
        return (0, 0, 0)
    return (int(time.get("volume") or 0), int(time.get("chapter") or 0), int(time.get("segment") or 0))


def _time_tuple_from_segment_id(segment_id: str | None, volume: int) -> tuple[int, int, int]:
    if segment_id:
        match = TIME_KEY_RE.match(segment_id)
        if match:
            return (int(match.group("volume")), int(match.group("chapter")), int(match.group("segment")))
    return (volume, 0, 0)


def _relationship_state_for_pair(
    project_root: str | Path,
    volume: int,
    segment_id: str | None,
    speaker: str | None,
    listener: str | None,
) -> dict[str, Any] | None:
    if not speaker or not listener:
        return None
    cursor = _time_tuple_from_segment_id(segment_id, volume)
    records: list[dict[str, Any]] = []
    for path in [resolve_project_path(project_root, "db", "series_relationships.json"), resolve_project_path(project_root, "db", volume_dir(volume), "relationships.json")]:
        if path.exists():
            records.extend(read_json(path, default=[]))
    latest: dict[str, Any] | None = None
    for row in sorted(records, key=lambda item: (_time_tuple_from_point(item.get("time")), item.get("relationship_ID", ""))):
        if row.get("speaker") != speaker or row.get("listener") != listener:
            continue
        if _time_tuple_from_point(row.get("time")) <= cursor:
            latest = row
    if not latest:
        return None
    return {
        "relationship_ID": latest.get("relationship_ID"),
        "type": latest.get("type"),
        "relationship": latest.get("relationship"),
        "pronoun": latest.get("pronoun"),
        "alias_pronoun": latest.get("alias_pronoun", []),
        "time": latest.get("time"),
        "conflict": latest.get("conflict", False),
    }


def _pronoun_context(project_root: str | Path, volume: int, item: PipelineItem | None) -> dict[str, Any] | None:
    if not item or item.type != "dialogue":
        return None
    label = _dialogue_label(project_root, volume, item.item_ID)
    if not label:
        return {"dialogue_label": None, "forward": None, "reverse": None}
    speaker = label.get("speaker")
    listener = label.get("listener")
    return {
        "dialogue_label": label,
        "forward": _relationship_state_for_pair(project_root, volume, item.segment_ID, speaker, listener),
        "reverse": _relationship_state_for_pair(project_root, volume, item.segment_ID, listener, speaker),
    }


def _replace_placeholders(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[{key}]", value)
    return rendered


def render_prompt(project_root: str | Path, request: PromptRenderRequest) -> PromptRenderResponse:
    ensure_prompt_files(project_root)
    config = TASK_CONFIG[request.task]
    template = read_prompt_file(project_root, config["template"])
    json_policy = read_prompt_file(project_root, "json_policy.md")
    scope = request.scope
    segment = _find_segment(project_root, scope.volume, scope.segment_ID)
    chapter = _find_chapter(project_root, scope.volume, scope.chapter or (segment.chapter if segment else None))
    item = _find_item(project_root, scope.volume, scope.item_ID)
    subitem = _find_subitem(project_root, scope.volume, scope.sub_item_ID)

    values = {
        "JSON_OUTPUT_POLICY": json_policy,
        "CHAPTER": chapter.chapter if chapter else "",
        "CHAPTER_NAME": chapter.name if chapter else "",
        "SOURCE_TEXT": chapter.content if chapter else "",
        "SUB_ITEM_ID": subitem.sub_item_ID if subitem else (scope.sub_item_ID or ""),
        "SUB_ITEM": subitem.text if subitem else "",
        "SEGMENT_ID": segment.segment_ID if segment else (scope.segment_ID or ""),
        "TIME_KEY": segment.segment_ID if segment else (scope.segment_ID or ""),
        "SEGMENT_TEXT": segment.content if segment else "",
        "GLOSSARY_SEGMENT_CHARACTERS": _json_dump(_segment_characters(project_root, scope.volume, scope.segment_ID)),
        "SEGMENT_ITEMS": _json_dump(_segment_items(project_root, scope.volume, scope.segment_ID)),
        "ITEM_ID": item.item_ID if item else (scope.item_ID or ""),
        "ITEM_TYPE": item.type if item else "",
        "ITEM_TEXT": item.text if item else "",
        "DIALOGUE_LABEL": _json_dump(_dialogue_label(project_root, scope.volume, scope.item_ID)),
        "PRONOUN_CONTEXT": _json_dump(_pronoun_context(project_root, scope.volume, item)),
        "GLOSSARY_FOR_ITEM": _json_dump(_item_glossary(project_root, scope.volume, scope.item_ID)),
    }
    return PromptRenderResponse(
        prompt=_replace_placeholders(template, values),
        expected_schema=config["expected_schema"],
        provider_slot=config["provider_slot"],  # type: ignore[arg-type]
    )


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return json.loads(stripped)


def _require_list(data: Any, errors: list[str]) -> list[Any]:
    if not isinstance(data, list):
        errors.append("Result must be a JSON array.")
        return []
    return data


def _pydantic_errors(exc: ValidationError) -> list[str]:
    messages = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        prefix = f"{location}: " if location else ""
        messages.append(f"{prefix}{error['msg']}")
    return messages


def _timeline_from_key(value: Any, scope: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return TimelinePoint.model_validate(value).model_dump(mode="json")
    if isinstance(value, str) and value.strip():
        match = TIME_KEY_RE.match(value.strip())
        if match:
            return TimelinePoint(
                volume=int(match.group("volume")),
                chapter=int(match.group("chapter")),
                segment=int(match.group("segment")),
                key=value.strip(),
            ).model_dump(mode="json")
    if scope.segment_ID:
        match = TIME_KEY_RE.match(scope.segment_ID)
        if match:
            return TimelinePoint(
                volume=int(match.group("volume")),
                chapter=int(match.group("chapter")),
                segment=int(match.group("segment")),
                key=scope.segment_ID,
            ).model_dump(mode="json")
    raise ValueError("time must be an object or a canonical segment key like v01_ch001_s001.")


def _normalize_dialogue_rows(project_root: str | Path, volume: int, rows: list[Any], errors: list[str]) -> list[Any]:
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"Row {index} must be an object.")
            continue
        next_row = dict(row)
        item = _find_item(project_root, volume, next_row.get("item_ID"))
        if not item:
            errors.append(f"Row {index} item_ID does not exist: {next_row.get('item_ID')}")
            continue
        if item.type != "dialogue":
            errors.append(f"Row {index} item_ID is not a dialogue item: {item.item_ID}")
            continue
        if not next_row.get("segment_ID"):
            next_row["segment_ID"] = item.segment_ID
        characters = {entry.get("glossary_ID") for entry in _segment_characters(project_root, volume, item.segment_ID)}
        for field_name in ["speaker", "listener"]:
            value = next_row.get(field_name)
            if value is not None and characters and value not in characters:
                errors.append(f"Row {index} {field_name} is not a segment character glossary_ID: {value}")
        if next_row.get("speaker") is None or next_row.get("listener") is None:
            next_row["human_review"] = True
        normalized.append(next_row)
    return normalized


def _normalize_result(project_root: str | Path, request: PromptResultRequest, data: Any, expected_schema: str) -> tuple[Any, list[str]]:
    errors: list[str] = []
    try:
        if expected_schema == "draft_glossary":
            rows = _require_list(data, errors)
            if errors:
                return data, errors
            for index, row in enumerate(rows, start=1):
                if isinstance(row, dict) and not row.get("draft_glossary_ID"):
                    row["draft_glossary_ID"] = f"dglo_{index:06d}"
            validated = draft_glossary_adapter.validate_python(rows)
            return draft_glossary_adapter.dump_python(validated, mode="json"), []
        if expected_schema == "relationships":
            rows = _require_list(data, errors)
            if errors:
                return data, errors
            normalized = []
            for row in rows:
                if not isinstance(row, dict):
                    errors.append("Each relationship row must be an object.")
                    continue
                next_row = dict(row)
                next_row["time"] = _timeline_from_key(next_row.get("time"), request.scope)
                normalized.append(next_row)
            if errors:
                return data, errors
            validated = relationship_result_adapter.validate_python(normalized)
            return relationship_result_adapter.dump_python(validated, mode="json"), []
        if expected_schema == "dialogue_labels":
            rows = _require_list(data, errors)
            if errors:
                return data, errors
            normalized = _normalize_dialogue_rows(project_root, request.scope.volume, rows, errors)
            if errors:
                return data, errors
            validated = dialogue_label_adapter.validate_python(normalized)
            return dialogue_label_adapter.dump_python(validated, mode="json"), []
        if expected_schema == "translation":
            if not isinstance(data, dict):
                return data, ["Translation result must be an object."]
            normalized = dict(data)
            if "item_ID" not in normalized and "item_id" in normalized:
                normalized["item_ID"] = normalized.pop("item_id")
            validated = translation_result_adapter.validate_python(normalized)
            return translation_result_adapter.dump_python(validated, mode="json"), []
        if expected_schema == "source_segments":
            rows = _require_list(data, errors)
            if errors:
                return data, errors
            validated = source_segment_draft_adapter.validate_python(rows)
            return source_segment_draft_adapter.dump_python(validated, mode="json"), []
    except (ValidationError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            return data, _pydantic_errors(exc)
        return data, [str(exc)]
    return data, [f"Unknown expected schema: {expected_schema}"]


def validate_prompt_result(project_root: str | Path, request: PromptResultRequest) -> PromptValidationResponse:
    expected_schema = TASK_CONFIG[request.task]["expected_schema"]
    try:
        data = _extract_json(request.result_text)
    except json.JSONDecodeError as exc:
        return PromptValidationResponse(
            ok=False,
            expected_schema=expected_schema,
            errors=[f"Invalid JSON: {exc.msg} at line {exc.lineno}."],
        )

    normalized, errors = _normalize_result(project_root, request, data, expected_schema)

    return PromptValidationResponse(
        ok=not errors,
        expected_schema=expected_schema,
        errors=errors,
        normalized=normalized,
    )


def _target_for_task(project_root: str | Path, request: PromptResultRequest) -> Path:
    volume_db = resolve_project_path(project_root, "db", volume_dir(request.scope.volume))
    volume_work = resolve_project_path(project_root, "work", volume_dir(request.scope.volume))
    if request.task == "extract_glossary":
        return volume_db / "draft_glossary.json"
    if request.task == "extract_relationship":
        return volume_db / "relationships.json"
    if request.task == "label_dialogue":
        return volume_db / "dialogue_labels.json"
    if request.task == "translate":
        return volume_db / "translations.json"
    return volume_work / "segment_source_result.json"


def save_prompt_result(project_root: str | Path, request: PromptResultRequest) -> PromptSaveResponse:
    validation = validate_prompt_result(project_root, request)
    if not validation.ok:
        return PromptSaveResponse(validation=validation, target_file="", records=0)
    target = _target_for_task(project_root, request)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = validation.normalized
    if request.task == "translate":
        assert isinstance(normalized, dict)
        record = Translation(
            item_ID=normalized["item_ID"],
            trans_text=normalized["trans_text"],
            updated_at=utc_now(),
        )
        existing = read_json_default(target, translation_adapter, [])
        existing = [row for row in existing if row.item_ID != record.item_ID]
        existing.append(record)
        write_json_atomic(target, existing, translation_adapter, project_root=project_root, backup=True)
        records = len(existing)
    elif request.task == "extract_relationship":
        rows = []
        for row in relationship_result_adapter.validate_python(normalized if isinstance(normalized, list) else [normalized]):
            relationship_id = row.relationship_ID or allocate_id(project_root, "relationship")
            rows.append(
                Relationship(
                    relationship_ID=relationship_id,
                    speaker=row.speaker,
                    listener=row.listener,
                    type=row.type,
                    relationship=row.relationship,
                    pronoun=row.pronoun,
                    alias_pronoun=row.alias_pronoun,
                    time=row.time,
                    source_segment_ID=row.source_segment_ID,
                    human_review=row.human_review,
                    conflict=row.conflict,
                    note=row.note,
                )
            )
        write_json_atomic(target, rows, relationship_adapter, project_root=project_root, backup=True)
        records = len(rows)
    else:
        rows = normalized if isinstance(normalized, list) else [normalized]
        adapter = {
            "extract_glossary": draft_glossary_adapter,
            "label_dialogue": dialogue_label_adapter,
            "segment_source": source_segment_draft_adapter,
        }[request.task]
        write_json_atomic(target, rows, adapter, project_root=project_root, backup=True)
        records = len(rows)
    return PromptSaveResponse(validation=validation, target_file=str(target), records=records)


def _jobs_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "work", volume_dir(volume), "llm_jobs.json")


def _save_job(project_root: str | Path, job: LLMJob) -> None:
    path = _jobs_path(project_root, job.scope.volume)
    jobs = read_json_default(path, llm_job_adapter, [])
    jobs = [row for row in jobs if row.job_ID != job.job_ID]
    jobs.append(job)
    write_json_atomic(path, jobs, llm_job_adapter)


def run_llm(project_root: str | Path, request: LLMRunRequest) -> LLMRunResponse:
    render = render_prompt(project_root, request)
    job = LLMJob(
        job_ID=allocate_id(project_root, "job"),
        task=request.task,
        provider_slot=render.provider_slot,
        scope=request.scope,
        status="running",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    _save_job(project_root, job)
    try:
        result = call_llm(ensure_app_settings(), render.provider_slot, render.prompt)
        job.status = "completed"
        job.updated_at = utc_now()
        _save_job(project_root, job)
        results_dir = resolve_project_path(project_root, "work", volume_dir(request.scope.volume), "llm_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / f"{job.job_ID}.txt").write_text(result, encoding="utf-8")
        return LLMRunResponse(job=job, render=render, result_text=result)
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.updated_at = utc_now()
        _save_job(project_root, job)
        raise
