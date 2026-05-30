from __future__ import annotations

from pathlib import Path

from app.schemas import PipelineState, PipelineStepState, utc_now
from app.storage import read_json, resolve_project_path, write_json_atomic
from app.storage.helpers import volume_dir


PIPELINE_STEP_ORDER = {
    "import_source": 0,
    "skeleton": 1,
    "sub_items": 2,
    "glossary_extract": 3,
    "glossary_merge": 4,
    "glossary_scan_items": 5,
    "glossary_scan_segments": 6,
    "relationships_extract": 7,
    "relationships_merge": 8,
    "dialogue_labels_extract": 9,
    "translate": 10,
}


def pipeline_state_path(project_root: str | Path, volume: int) -> Path:
    return resolve_project_path(project_root, "work", volume_dir(volume), "pipeline_state.json")


def load_pipeline_state(project_root: str | Path, volume: int) -> PipelineState:
    path = pipeline_state_path(project_root, volume)
    if path.exists():
        return read_json(path, PipelineState)
    return PipelineState(volume=volume, volume_ID=f"v{volume:02d}", steps=[])


def upsert_pipeline_step(state: PipelineState, step: PipelineStepState) -> PipelineState:
    state.steps = [existing for existing in state.steps if existing.name != step.name]
    state.steps.append(step)
    state.steps.sort(key=lambda item: PIPELINE_STEP_ORDER.get(item.name, 99))
    state.updated_at = utc_now()
    return state


def save_pipeline_state(project_root: str | Path, volume: int, state: PipelineState) -> PipelineState:
    state.steps.sort(key=lambda item: PIPELINE_STEP_ORDER.get(item.name, 99))
    state.updated_at = utc_now()
    path = pipeline_state_path(project_root, volume)
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_json_atomic(path, state, PipelineState)


def set_pipeline_step(
    project_root: str | Path,
    volume: int,
    name: str,
    status: str,
    message: str,
    metrics: dict[str, int] | None = None,
) -> PipelineState:
    state = load_pipeline_state(project_root, volume)
    upsert_pipeline_step(
        state,
        PipelineStepState(
            name=name,
            status=status,  # type: ignore[arg-type]
            message=message,
            updated_at=utc_now(),
            metrics=metrics or {},
        ),
    )
    return save_pipeline_state(project_root, volume, state)
