from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
import math
from pathlib import Path

from pydantic import TypeAdapter

from app.llm import call_llm
from app.pipeline import load_items
from app.pipeline.state import set_pipeline_step
from app.prompts.service import render_prompt, validate_prompt_result
from app.projects import ensure_app_settings, load_project_settings
from app.schemas import (
    PipelineRunResponse,
    PromptRenderRequest,
    PromptResultRequest,
    PromptScope,
    Translation,
    TranslationJob,
    TranslationRunRequest,
    TranslationTableResponse,
    TranslationUpdateRequest,
    utc_now,
)
from app.storage import write_json_atomic
from app.storage.helpers import db_volume_dir, read_json_default, work_volume_dir


translation_adapter = TypeAdapter(list[Translation])
job_adapter = TypeAdapter(list[TranslationJob])

def _db_dir(project_root: str | Path, volume: int) -> Path:
    return db_volume_dir(project_root, volume)


def _work_dir(project_root: str | Path, volume: int) -> Path:
    return work_volume_dir(project_root, volume)


def _translations_path(project_root: str | Path, volume: int) -> Path:
    return _db_dir(project_root, volume) / "translations.json"


def _jobs_path(project_root: str | Path, volume: int) -> Path:
    return _work_dir(project_root, volume) / "translation_jobs.json"


def _load_translations(project_root: str | Path, volume: int) -> list[Translation]:
    return read_json_default(_translations_path(project_root, volume), translation_adapter, [])


def _load_jobs(project_root: str | Path, volume: int) -> list[TranslationJob]:
    return read_json_default(_jobs_path(project_root, volume), job_adapter, [])


def _save_translations(project_root: str | Path, volume: int, rows: list[Translation]) -> None:
    rows.sort(key=lambda row: row.item_ID)
    write_json_atomic(_translations_path(project_root, volume), rows, translation_adapter, project_root=project_root, backup=True)


def _save_jobs(project_root: str | Path, volume: int, rows: list[TranslationJob]) -> None:
    rows.sort(key=lambda row: row.item_ID)
    write_json_atomic(_jobs_path(project_root, volume), rows, job_adapter, project_root=project_root, backup=True)


def _translate_one(project_root: str | Path, volume: int, item_id: str) -> Translation:
    render = render_prompt(project_root, PromptRenderRequest(task="translate", scope=PromptScope(volume=volume, item_ID=item_id)))
    raw = call_llm(ensure_app_settings(), render.provider_slot, render.prompt)
    results_dir = _work_dir(project_root, volume) / "llm_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / f"translate_{item_id}.txt").write_text(raw, encoding="utf-8")
    validation = validate_prompt_result(
        project_root,
        PromptResultRequest(task="translate", scope=PromptScope(volume=volume, item_ID=item_id), result_text=raw),
    )
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    normalized = validation.normalized
    if not isinstance(normalized, dict):
        raise ValueError("Translation result must normalize to an object.")
    return Translation(item_ID=normalized["item_ID"], trans_text=normalized["trans_text"], updated_at=utc_now())


def _run_selected(project_root: str | Path, volume: int, item_ids: list[str], overwrite: bool) -> PipelineRunResponse:
    existing_by_id = {row.item_ID: row for row in _load_translations(project_root, volume)}
    job_by_id = {row.item_ID: row for row in _load_jobs(project_root, volume)}
    selected = [item_id for item_id in item_ids if overwrite or item_id not in existing_by_id]
    if not selected:
        state = set_pipeline_step(
            project_root,
            volume,
            "translate",
            "completed",
            "No pending translations",
            {"total": len(item_ids), "completed": len(existing_by_id), "failed": 0, "pending": 0},
        )
        return PipelineRunResponse(volume=volume, pipeline_state=state, counts=state.steps[-1].metrics, warnings=[])

    app_settings = ensure_app_settings()
    project_settings = load_project_settings(project_root)
    batch_count = project_settings.batch_count_override or app_settings.batch_count
    max_workers = max(1, min(batch_count, len(selected)))
    warnings: list[str] = []

    for item_id in selected:
        current = job_by_id.get(item_id) or TranslationJob(item_ID=item_id)
        job_by_id[item_id] = current.model_copy(update={"status": "running", "updated_at": utc_now()})
    _save_jobs(project_root, volume, list(job_by_id.values()))

    batch_timeout = max(150, math.ceil(len(selected) / max_workers) * 150)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_translate_one, project_root, volume, item_id): item_id for item_id in selected}
        try:
            completed_futures = as_completed(futures, timeout=batch_timeout)
            for future in completed_futures:
                item_id = futures[future]
                current = job_by_id[item_id]
                try:
                    translation = future.result()
                    existing_by_id[translation.item_ID] = translation
                    job_by_id[item_id] = current.model_copy(
                        update={"status": "completed", "attempts": current.attempts + 1, "error": None, "updated_at": utc_now()}
                    )
                except Exception as exc:
                    job_by_id[item_id] = current.model_copy(
                        update={"status": "failed", "attempts": current.attempts + 1, "error": str(exc), "updated_at": utc_now()}
                    )
                    warnings.append(f"translation_failed:{item_id}:{exc}")
        except TimeoutError:
            for future, item_id in futures.items():
                if future.done():
                    continue
                future.cancel()
                current = job_by_id[item_id]
                job_by_id[item_id] = current.model_copy(
                    update={
                        "status": "failed",
                        "attempts": current.attempts + 1,
                        "error": f"Translation batch timed out after {batch_timeout} seconds.",
                        "updated_at": utc_now(),
                    }
                )
                warnings.append(f"translation_timeout:{item_id}")

    _save_translations(project_root, volume, list(existing_by_id.values()))
    _save_jobs(project_root, volume, list(job_by_id.values()))
    failed = sum(1 for row in job_by_id.values() if row.item_ID in selected and row.status == "failed")
    pending = len(item_ids) - len(existing_by_id)
    metrics = {
        "total": len(item_ids),
        "completed": len(existing_by_id),
        "failed": failed,
        "pending": max(pending, 0),
        "batch_count": batch_count,
    }
    state = set_pipeline_step(
        project_root,
        volume,
        "translate",
        "needs_review" if failed else "completed",
        f"{len(existing_by_id)} translations completed",
        metrics,
    )
    return PipelineRunResponse(volume=volume, pipeline_state=state, counts=metrics, warnings=warnings)


def run_translation_pipeline(project_root: str | Path, volume: int, request: TranslationRunRequest | None = None) -> PipelineRunResponse:
    request = request or TranslationRunRequest()
    items = load_items(project_root, volume)
    all_ids = [item.item_ID for item in items]
    requested_ids = request.item_ID or all_ids
    valid_ids = [item_id for item_id in requested_ids if item_id in set(all_ids)]
    return _run_selected(project_root, volume, valid_ids, request.overwrite)


def retry_failed_translations(project_root: str | Path, volume: int) -> PipelineRunResponse:
    failed_ids = [job.item_ID for job in _load_jobs(project_root, volume) if job.status == "failed"]
    return _run_selected(project_root, volume, failed_ids, overwrite=True)


def get_translations(project_root: str | Path, volume: int) -> TranslationTableResponse:
    return TranslationTableResponse(volume=volume, translations=_load_translations(project_root, volume), jobs=_load_jobs(project_root, volume))


def update_translation(project_root: str | Path, volume: int, item_id: str, request: TranslationUpdateRequest) -> Translation:
    items = {item.item_ID for item in load_items(project_root, volume)}
    if item_id not in items:
        raise KeyError(f"Translation item_ID does not exist: {item_id}")
    rows = _load_translations(project_root, volume)
    updated = Translation(item_ID=item_id, trans_text=request.trans_text, updated_at=utc_now())
    rows = [row for row in rows if row.item_ID != item_id]
    rows.append(updated)
    _save_translations(project_root, volume, rows)
    return updated
