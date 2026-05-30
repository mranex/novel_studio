from __future__ import annotations

import logging

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import APP_VERSION
from app.dialogue import extract_dialogue_labels, get_dialogue_labels, update_dialogue_label
from app.database import (
    get_series_table as get_generic_series_table,
    get_volume_table as get_generic_volume_table,
    list_db_tables,
    patch_volume_row,
    put_series_table,
    put_volume_table,
    validate_series_table,
    validate_volume_table,
)
from app.glossary import (
    extract_draft_glossary,
    get_volume_table,
    merge_draft_glossary,
    scan_item_glossary,
    scan_segment_glossary,
    update_glossary_entry,
)
from app.ids import allocate_id
from app.imports import commit_import, commit_segment_file, commit_source_file, load_manifest, validate_import
from app.pipeline import build_skeleton, build_subitems, load_items, load_subitems
from app.polish import export_project, get_polish_preview, save_polish_override
from app.prompts import (
    list_prompt_files,
    read_prompt_file,
    render_prompt,
    run_llm,
    save_prompt_result,
    update_prompt_file,
    validate_prompt_result,
)
from app.projects import (
    create_project,
    ensure_app_settings,
    app_home,
    get_project_detail,
    list_projects,
    load_project_settings,
    load_workflow_states,
    open_project,
    project_root_for_id,
    update_app_settings,
    update_project_metadata,
    update_project_settings,
)
from app.relationships import (
    create_relationship,
    extract_relationships,
    get_relationship_canvas,
    get_relationship_state,
    merge_relationships,
    save_relationship_layout,
    update_relationship,
)
from app.schemas import (
    AppSettings,
    DbRowPatchRequest,
    DbTableUpdateRequest,
    ExportRequest,
    GlossaryMergeRequest,
    GlossaryUpdateRequest,
    ImportCommitRequest,
    ImportFilePayload,
    ImportValidateRequest,
    DialogueLabelUpdateRequest,
    LLMRunRequest,
    PromptFileUpdate,
    PromptRenderRequest,
    PromptResultRequest,
    ProjectCreateRequest,
    ProjectMetadataUpdateRequest,
    ProjectOpenRequest,
    ProjectSettingsUpdateRequest,
    ProviderTestRequest,
    ProviderTestResponse,
    PolishOverrideRequest,
    RelationshipCreateRequest,
    RelationshipLayoutRequest,
    RelationshipUpdateRequest,
    TranslationRunRequest,
    TranslationUpdateRequest,
)
from app.series import apply_series_update, preview_series_update
from app.translation import get_translations, retry_failed_translations, run_translation_pipeline, update_translation


app = FastAPI(title="Novel Translation Studio API", version=APP_VERSION)
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    app_logger = logging.getLogger("app")
    if app_logger.handlers:
        return
    log_dir = app_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "novel-studio.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)


configure_logging()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(KeyError)
async def key_error_handler(_request: Request, exc: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(_request: Request, exc: FileNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app_version": APP_VERSION}


@app.get("/api/settings")
def settings(project_root: str | None = Query(default=None)) -> dict[str, object]:
    response: dict[str, object] = {"app": ensure_app_settings().model_dump(mode="json")}
    if project_root:
        response["project"] = load_project_settings(project_root).model_dump(mode="json")
    return response


@app.put("/api/settings")
def put_settings(request: AppSettings):
    return update_app_settings(request)


@app.post("/api/settings/test")
def post_settings_test(request: ProviderTestRequest) -> ProviderTestResponse:
    settings = ensure_app_settings()
    provider = getattr(settings, request.provider_slot)
    if not provider.base_url.strip():
        return ProviderTestResponse(ok=False, provider_slot=request.provider_slot, message="Base URL is required.")
    headers = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    try:
        response = httpx.get(provider.base_url.rstrip("/") + "/models", headers=headers, timeout=10)
        response.raise_for_status()
        return ProviderTestResponse(ok=True, provider_slot=request.provider_slot, message="Connection succeeded.")
    except Exception as exc:
        logger.exception("Provider connection test failed for %s", request.provider_slot)
        return ProviderTestResponse(ok=False, provider_slot=request.provider_slot, message=str(exc))


@app.post("/api/projects")
def post_project(request: ProjectCreateRequest):
    return create_project(request)


@app.get("/api/projects")
def get_projects():
    return {"projects": [project.model_dump(mode="json") for project in list_projects()]}


@app.post("/api/projects/open")
def post_project_open(request: ProjectOpenRequest):
    return open_project(request)


@app.get("/api/projects/workflow")
def workflow(project_root: str = Query(...)):
    return {"volumes": [volume.model_dump(mode="json") for volume in load_workflow_states(project_root)]}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    try:
        return get_project_detail(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/metadata")
def put_project_metadata(project_id: str, request: ProjectMetadataUpdateRequest):
    try:
        return update_project_metadata(project_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/settings")
def put_project_settings(project_id: str, request: ProjectSettingsUpdateRequest):
    try:
        return update_project_settings(project_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/import/source")
def post_import_source(project_id: str, payload: ImportFilePayload):
    try:
        return commit_source_file(project_root_for_id(project_id), payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/import/segment")
def post_import_segment(project_id: str, payload: ImportFilePayload):
    try:
        return commit_segment_file(project_root_for_id(project_id), payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/import/validate")
def post_import_validate(project_id: str, request: ImportValidateRequest):
    try:
        project_root_for_id(project_id)
        return validate_import(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/import/commit")
def post_import_commit(project_id: str, request: ImportCommitRequest):
    try:
        return commit_import(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/import/manifest")
def get_import_manifest(project_id: str):
    try:
        return load_manifest(project_root_for_id(project_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/skeleton")
def post_pipeline_skeleton(project_id: str, volume: int):
    try:
        return build_skeleton(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing imported segment file: {exc}") from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/subitems")
def post_pipeline_subitems(project_id: str, volume: int):
    try:
        return build_subitems(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Run skeleton builder first: {exc}") from exc


@app.get("/api/projects/{project_id}/pipeline/{volume}/items")
def get_pipeline_items(project_id: str, volume: int):
    try:
        return {"items": [item.model_dump(mode="json") for item in load_items(project_root_for_id(project_id), volume)]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/pipeline/{volume}/subitems")
def get_pipeline_subitems(project_id: str, volume: int):
    try:
        return {"sub_items": [item.model_dump(mode="json") for item in load_subitems(project_root_for_id(project_id), volume)]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/glossary/extract")
def post_glossary_extract(project_id: str, volume: int):
    try:
        return extract_draft_glossary(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Run sub-item splitter first: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Glossary extraction failed for project=%s volume=%s", project_id, volume)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/glossary/merge")
def post_glossary_merge(project_id: str, volume: int, request: GlossaryMergeRequest | None = None):
    try:
        return merge_draft_glossary(project_root_for_id(project_id), volume, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing draft glossary or sub-items: {exc}") from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/glossary/scan-items")
def post_glossary_scan_items(project_id: str, volume: int):
    try:
        return scan_item_glossary(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing glossary or items: {exc}") from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/glossary/scan-segments")
def post_glossary_scan_segments(project_id: str, volume: int):
    try:
        return scan_segment_glossary(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Run item glossary scanner first: {exc}") from exc


@app.get("/api/projects/{project_id}/db/volumes/{volume}/{table}")
def get_db_volume_table(project_id: str, volume: int, table: str):
    try:
        return get_generic_volume_table(project_root_for_id(project_id), volume, table)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/db/tables")
def get_db_tables(project_id: str):
    try:
        return {"tables": [row.model_dump(mode="json") for row in list_db_tables(project_root_for_id(project_id))]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/db/volumes/{volume}/{table}")
def put_db_volume_table(project_id: str, volume: int, table: str, request: DbTableUpdateRequest):
    try:
        return put_volume_table(project_root_for_id(project_id), volume, table, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/projects/{project_id}/db/volumes/{volume}/glossary/{glossary_id}")
def patch_glossary_entry(project_id: str, volume: int, glossary_id: str, request: GlossaryUpdateRequest):
    try:
        return update_glossary_entry(project_root_for_id(project_id), volume, glossary_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/projects/{project_id}/db/volumes/{volume}/{table}/{row_id}")
def patch_db_volume_row(project_id: str, volume: int, table: str, row_id: str, request: DbRowPatchRequest):
    try:
        return patch_volume_row(project_root_for_id(project_id), volume, table, row_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/db/volumes/{volume}/{table}/validate")
def post_db_volume_validate(project_id: str, volume: int, table: str, request: DbTableUpdateRequest):
    try:
        return validate_volume_table(project_root_for_id(project_id), volume, table, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/db/series/{table}")
def get_db_series_table(project_id: str, table: str):
    try:
        return get_generic_series_table(project_root_for_id(project_id), table)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/db/series/{table}")
def put_db_series_table(project_id: str, table: str, request: DbTableUpdateRequest):
    try:
        return put_series_table(project_root_for_id(project_id), table, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/db/series/{table}/validate")
def post_db_series_validate(project_id: str, table: str, request: DbTableUpdateRequest):
    try:
        return validate_series_table(project_root_for_id(project_id), table, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/relationships/extract")
def post_relationships_extract(project_id: str, volume: int):
    try:
        return extract_relationships(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing segment or glossary data: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Relationship extraction failed for project=%s volume=%s", project_id, volume)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/relationships/merge")
def post_relationships_merge(project_id: str, volume: int):
    try:
        return merge_relationships(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/relationships/state")
def get_relationships_state(project_id: str, time_key: str = Query(...), scope: str = Query(default="series")):
    try:
        if scope not in {"series", "volume"}:
            raise ValueError("scope must be series or volume")
        return {
            "time_key": time_key,
            "relationships": [
                row.model_dump(mode="json")
                for row in get_relationship_state(project_root_for_id(project_id), time_key, scope)  # type: ignore[arg-type]
            ],
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/relationships/canvas")
def get_relationships_canvas(project_id: str, time_key: str = Query(...), scope: str = Query(default="series")):
    try:
        if scope not in {"series", "volume"}:
            raise ValueError("scope must be series or volume")
        return get_relationship_canvas(project_root_for_id(project_id), time_key, scope)  # type: ignore[arg-type]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/projects/{project_id}/relationships/{relationship_id}")
def patch_relationship(project_id: str, relationship_id: str, request: RelationshipUpdateRequest):
    try:
        return update_relationship(project_root_for_id(project_id), relationship_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/relationships")
def post_relationship(project_id: str, request: RelationshipCreateRequest):
    try:
        return create_relationship(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/relationships/layout")
def put_relationship_layout(project_id: str, request: RelationshipLayoutRequest):
    try:
        return save_relationship_layout(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/dialogue-labels/extract")
def post_dialogue_labels_extract(project_id: str, volume: int):
    try:
        return extract_dialogue_labels(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing segment or skeleton data: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Dialogue label extraction failed for project=%s volume=%s", project_id, volume)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/translate")
def post_translate(project_id: str, volume: int, request: TranslationRunRequest | None = None):
    try:
        return run_translation_pipeline(project_root_for_id(project_id), volume, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing translation input: {exc}") from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/translate/retry-failed")
def post_translate_retry_failed(project_id: str, volume: int):
    try:
        return retry_failed_translations(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/translations")
def get_project_translations(project_id: str, volume: int = Query(default=1)):
    try:
        return get_translations(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/api/projects/{project_id}/translations/{item_id}")
def patch_translation(project_id: str, item_id: str, request: TranslationUpdateRequest, volume: int = Query(default=1)):
    try:
        return update_translation(project_root_for_id(project_id), volume, item_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/series/preview")
def post_series_preview(project_id: str, volume: int):
    try:
        return preview_series_update(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/series/update")
def post_series_update(project_id: str, volume: int):
    try:
        return apply_series_update(project_root_for_id(project_id), volume)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/polish/preview")
def get_project_polish_preview(project_id: str, volume: int = Query(default=1), chapter: str | None = Query(default=None)):
    try:
        return get_polish_preview(project_root_for_id(project_id), volume, chapter)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing polish input: {exc}") from exc


@app.patch("/api/projects/{project_id}/polish/{item_id}")
def patch_polish_override(project_id: str, item_id: str, request: PolishOverrideRequest, volume: int = Query(default=1)):
    try:
        return save_polish_override(project_root_for_id(project_id), volume, item_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/pipeline/{volume}/regenerate")
def post_regenerate(project_id: str, volume: int):
    try:
        preview = get_polish_preview(project_root_for_id(project_id), volume)
        return {"volume": volume, "chapter": preview.chapter, "items": len(preview.items), "missing": sum(1 for item in preview.items if item.missing)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Missing polish input: {exc}") from exc


@app.post("/api/projects/{project_id}/export")
def post_export(project_id: str, request: ExportRequest):
    try:
        return export_project(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/export/{volume}")
def post_export_volume(project_id: str, volume: int, request: ExportRequest):
    try:
        return export_project(project_root_for_id(project_id), request.model_copy(update={"scope": "volume", "volumes": [volume]}))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/dialogue-labels")
def get_project_dialogue_labels(project_id: str, volume: int = Query(default=1), segment_ID: str | None = Query(default=None)):
    try:
        return get_dialogue_labels(project_root_for_id(project_id), volume, segment_ID)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"Run skeleton builder first: {exc}") from exc


@app.patch("/api/projects/{project_id}/dialogue-labels/{item_id}")
def patch_dialogue_label(project_id: str, item_id: str, request: DialogueLabelUpdateRequest):
    try:
        return update_dialogue_label(project_root_for_id(project_id), item_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/prompts")
def get_prompts(project_id: str):
    try:
        return {"prompts": [item.model_dump(mode="json") for item in list_prompt_files(project_root_for_id(project_id))]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/prompts/{name}")
def get_prompt(project_id: str, name: str):
    try:
        return {"name": name, "content": read_prompt_file(project_root_for_id(project_id), name)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/projects/{project_id}/prompts/{name}")
def put_prompt(project_id: str, name: str, payload: PromptFileUpdate):
    try:
        return {"name": name, "content": update_prompt_file(project_root_for_id(project_id), name, payload.content)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/prompts/render")
def post_prompt_render(project_id: str, request: PromptRenderRequest):
    try:
        return render_prompt(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/llm/run")
def post_llm_run(project_id: str, request: LLMRunRequest):
    try:
        return run_llm(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("LLM run failed for project=%s task=%s", project_id, request.task)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/prompts/validate-result")
def post_prompt_validate(project_id: str, request: PromptResultRequest):
    try:
        project_root = project_root_for_id(project_id)
        return validate_prompt_result(project_root, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/{project_id}/prompts/save-result")
def post_prompt_save(project_id: str, request: PromptResultRequest):
    try:
        return save_prompt_result(project_root_for_id(project_id), request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/projects/ids/{kind}")
def post_id(kind: str, project_root: str = Query(...)) -> dict[str, str]:
    if kind not in {"glossary", "relationship", "job"}:
        raise HTTPException(status_code=400, detail="kind must be glossary, relationship, or job")
    return {"id": allocate_id(project_root, kind)}  # type: ignore[arg-type]
