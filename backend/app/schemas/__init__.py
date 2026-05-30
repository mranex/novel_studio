from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LLMProviderSettings(StrictModel):
    base_url: str
    api_key: str = ""
    model: str = ""


class AppSettings(StrictModel):
    small_llm: LLMProviderSettings = Field(
        default_factory=lambda: LLMProviderSettings(base_url="http://localhost:1234/v1")
    )
    big_llm: LLMProviderSettings = Field(
        default_factory=lambda: LLMProviderSettings(base_url="https://api.openai.com/v1")
    )
    batch_count: int = Field(default=8, ge=1)
    theme: Literal["dark", "light"] = "dark"


class ProviderTestRequest(StrictModel):
    provider_slot: Literal["small_llm", "big_llm"]


class ProviderTestResponse(StrictModel):
    ok: bool
    provider_slot: Literal["small_llm", "big_llm"]
    message: str


class ProjectSettings(StrictModel):
    max_subitem_tokens: int = Field(default=1200, ge=1)
    batch_count_override: int | None = Field(default=None, ge=1)
    prompt_folder: str = "prompt"


class ProjectSettingsUpdateRequest(StrictModel):
    max_subitem_tokens: int = Field(default=1200, ge=1)
    batch_count_override: int | None = Field(default=None, ge=1)
    prompt_folder: str = "prompt"


class ProjectMetadata(StrictModel):
    project_ID: str
    name: str
    genre: str
    source_language: str
    target_language: str
    notes: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    app_version: str = "0.1.0"

    @field_validator("project_ID")
    @classmethod
    def project_id_has_prefix(cls, value: str) -> str:
        if not value.startswith("proj_"):
            raise ValueError("project_ID must start with proj_")
        return value


class SourceChapter(StrictModel):
    chapter: str
    name: str = ""
    content: str


class SourceSegment(StrictModel):
    chapter: str
    name: str = ""
    segment: str
    segment_ID: str
    content: str


class Item(StrictModel):
    item_ID: str
    segment_ID: str
    chapter: str
    type: Literal["narration", "dialogue"]
    order: int = Field(ge=1)
    text: str
    needs_review: bool = False
    confidence: Literal["high", "low"] = "high"
    warnings: list[str] = Field(default_factory=list)


class SubItem(StrictModel):
    sub_item_ID: str
    item_ID: str
    segment_ID: str
    order: int = Field(ge=1)
    text: str


class TimelinePoint(StrictModel):
    volume: int = Field(ge=1)
    chapter: int | None = Field(default=None, ge=1)
    segment: int | None = Field(default=None, ge=1)
    key: str | None = None


class FirstSeen(StrictModel):
    volume: int = Field(ge=1)
    chapter: int | None = Field(default=None, ge=1)
    segment: int | None = Field(default=None, ge=1)
    key: str | None = None


class GlossaryEntry(StrictModel):
    glossary_ID: str
    volume: int | None = Field(default=None, ge=1)
    source: str
    trans: str = ""
    type: str
    alias: list[str] = Field(default_factory=list)
    human_review: bool = False
    link: list[str] = Field(default_factory=list)
    item_ID: list[str] = Field(default_factory=list)
    segment_ID: list[str] = Field(default_factory=list)
    time: TimelinePoint | None = None
    ready_for_series_update: bool = False
    first_seen: FirstSeen | None = None
    last_reviewed: datetime | None = None

    @field_validator("glossary_ID")
    @classmethod
    def glossary_id_has_prefix(cls, value: str) -> str:
        if not value.startswith("glo_"):
            raise ValueError("glossary_ID must start with glo_")
        return value


GlossaryType = Literal[
    "character",
    "alias",
    "title",
    "epithet",
    "location",
    "organization",
    "weapon",
    "artifact",
    "magic",
    "skill",
    "technique",
    "named_attack",
    "concept",
    "other",
]


class DraftGlossaryEntry(StrictModel):
    draft_glossary_ID: str | None = None
    sub_item_ID: str
    source: str
    type: GlossaryType

    @field_validator("draft_glossary_ID")
    @classmethod
    def draft_glossary_id_has_prefix(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("dglo_"):
            raise ValueError("draft_glossary_ID must start with dglo_")
        return value


class GlossaryMergeGroup(StrictModel):
    group_key: str
    source: str
    type: GlossaryType
    draft_glossary_ID: list[str] = Field(default_factory=list)
    sub_item_ID: list[str] = Field(default_factory=list)
    count: int = Field(ge=1)
    inherited_glossary_ID: str | None = None
    suggested_trans: str = ""
    approved: bool = False
    rejected: bool = False


class GlossaryMergeRequest(StrictModel):
    approved_group_keys: list[str] = Field(default_factory=list)
    rejected_group_keys: list[str] = Field(default_factory=list)


class GlossaryMergeResponse(StrictModel):
    volume: int
    groups: list[GlossaryMergeGroup]
    created: list[GlossaryEntry] = Field(default_factory=list)
    glossary: list[GlossaryEntry] = Field(default_factory=list)


class GlossaryUpdateRequest(StrictModel):
    trans: str | None = None
    type: GlossaryType | None = None
    alias: list[str] | None = None
    link: list[str] | None = None
    human_review: bool | None = None
    ready_for_series_update: bool | None = None


class ItemGlossaryEntry(StrictModel):
    item_ID: str
    glossary_ID: list[str] = Field(default_factory=list)


class SegmentGlossaryEntry(StrictModel):
    segment_ID: str
    glossary_ID: list[str] = Field(default_factory=list)


class GlossaryTableResponse(StrictModel):
    table: str
    volume: int
    rows: list[Any]


class Relationship(StrictModel):
    relationship_ID: str
    speaker: str
    listener: str
    type: Literal["ally", "enemy", "neutral", "unknown", "love", "family"] = "unknown"
    relationship: str = ""
    pronoun: str | None = None
    alias_pronoun: list[str] = Field(default_factory=list)
    time: TimelinePoint
    source_segment_ID: str
    human_review: bool = False
    conflict: bool = False
    note: str = ""
    ready_for_series_update: bool = False

    @field_validator("relationship_ID")
    @classmethod
    def relationship_id_has_prefix(cls, value: str) -> str:
        if not value.startswith("rel_"):
            raise ValueError("relationship_ID must start with rel_")
        return value


class PromptRelationshipResult(StrictModel):
    relationship_ID: str | None = None
    speaker: str
    listener: str
    type: Literal["ally", "enemy", "neutral", "unknown", "love", "family"] = "unknown"
    relationship: str = ""
    pronoun: str | None = None
    alias_pronoun: list[str] = Field(default_factory=list)
    time: TimelinePoint
    source_segment_ID: str
    human_review: bool = False
    conflict: bool = False
    note: str = ""

    @field_validator("relationship_ID")
    @classmethod
    def prompt_relationship_id_has_prefix(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("rel_"):
            raise ValueError("relationship_ID must start with rel_")
        return value


class RelationshipUpdateRequest(StrictModel):
    type: Literal["ally", "enemy", "neutral", "unknown", "love", "family"] | None = None
    relationship: str | None = None
    pronoun: str | None = None
    alias_pronoun: list[str] | None = None
    human_review: bool | None = None
    conflict: bool | None = None
    note: str | None = None
    ready_for_series_update: bool | None = None


class RelationshipCreateRequest(StrictModel):
    speaker: str
    listener: str
    type: Literal["ally", "enemy", "neutral", "unknown", "love", "family"] = "unknown"
    relationship: str = ""
    pronoun: str | None = None
    alias_pronoun: list[str] = Field(default_factory=list)
    time: TimelinePoint
    source_segment_ID: str
    human_review: bool = True
    conflict: bool = False
    note: str = ""


class RelationshipNode(StrictModel):
    id: str
    label: str
    source: str
    trans: str = ""
    conflict: bool = False
    x: float | None = None
    y: float | None = None


class RelationshipEdge(StrictModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    conflict: bool = False
    relationships: list[Relationship] = Field(default_factory=list)


class RelationshipCanvasResponse(StrictModel):
    time_key: str
    timeline: list[str] = Field(default_factory=list)
    nodes: list[RelationshipNode] = Field(default_factory=list)
    edges: list[RelationshipEdge] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)


class RelationshipLayoutNode(StrictModel):
    id: str
    x: float
    y: float


class RelationshipLayoutRequest(StrictModel):
    volume: int = Field(ge=1)
    nodes: list[RelationshipLayoutNode] = Field(default_factory=list)


class DialogueLabel(StrictModel):
    item_ID: str
    segment_ID: str
    speaker: str | None = None
    listener: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    human_review: bool = False
    note: str = ""


class DialogueLabelUpdateRequest(StrictModel):
    speaker: str | None = None
    listener: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    human_review: bool | None = None
    note: str | None = None


class DialogueLabelReviewItem(StrictModel):
    item_ID: str
    segment_ID: str
    text: str
    speaker: str | None = None
    listener: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    human_review: bool = False
    note: str = ""


class DialogueLabelReviewResponse(StrictModel):
    volume: int
    segment_ID: str | None = None
    labels: list[DialogueLabelReviewItem] = Field(default_factory=list)
    characters: list[GlossaryEntry] = Field(default_factory=list)
    segments: list[str] = Field(default_factory=list)


class Translation(StrictModel):
    item_ID: str
    trans_text: str
    updated_at: datetime = Field(default_factory=utc_now)


class PromptTranslationResult(StrictModel):
    item_ID: str
    trans_text: str


class TranslationJob(StrictModel):
    item_ID: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    attempts: int = Field(default=0, ge=0)
    error: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class TranslationRunRequest(StrictModel):
    item_ID: list[str] | None = None
    overwrite: bool = False


class TranslationUpdateRequest(StrictModel):
    trans_text: str


class TranslationTableResponse(StrictModel):
    volume: int
    translations: list[Translation] = Field(default_factory=list)
    jobs: list[TranslationJob] = Field(default_factory=list)


class PolishOverride(StrictModel):
    item_ID: str
    text: str
    updated_at: datetime = Field(default_factory=utc_now)


class PolishOverrideRequest(StrictModel):
    text: str


class PolishPreviewItem(StrictModel):
    item_ID: str
    segment_ID: str
    type: Literal["narration", "dialogue"]
    source_text: str
    translation_text: str | None = None
    polished_text: str | None = None
    preview_text: str
    missing: bool = False


class PolishChapterPreview(StrictModel):
    volume: int
    chapter: str
    chapter_name: str = ""
    text: str
    items: list[PolishPreviewItem] = Field(default_factory=list)


class ExportRequest(StrictModel):
    format: Literal["txt", "md", "html"]
    scope: Literal["volume", "selected_volumes", "series"] = "volume"
    volumes: list[int] = Field(default_factory=list)


class ExportResponse(StrictModel):
    format: str
    scope: str
    path: str
    volumes: list[int]
    missing_translations: int = 0


class SeriesGlossaryChange(StrictModel):
    action: Literal["new", "updated", "inherited"]
    source: str
    glossary_ID: str
    before: GlossaryEntry | None = None
    after: GlossaryEntry


class SeriesRelationshipChange(StrictModel):
    action: Literal["new_timestamp", "skipped_duplicate", "conflict"]
    relationship_ID: str
    speaker: str
    listener: str
    before: Relationship | None = None
    after: Relationship


class SeriesUpdatePreview(StrictModel):
    volume: int
    new_glossary_entries: int = 0
    updated_glossary_entries: int = 0
    inherited_glossary_entries: int = 0
    new_relationship_timestamps: int = 0
    skipped_duplicate_relationship_states: int = 0
    conflicts_needing_review: int = 0
    glossary_changes: list[SeriesGlossaryChange] = Field(default_factory=list)
    relationship_changes: list[SeriesRelationshipChange] = Field(default_factory=list)


class SeriesUpdateResponse(StrictModel):
    preview: SeriesUpdatePreview
    series_glossary_rows: int
    series_relationship_rows: int
    backups: list[str] = Field(default_factory=list)


class DbTableInfo(StrictModel):
    scope: Literal["volume", "series"]
    name: str
    volume: int | None = None
    path: str
    rows: int


class DbTableResponse(StrictModel):
    scope: Literal["volume", "series"]
    table: str
    volume: int | None = None
    rows: list[Any] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DbTableUpdateRequest(StrictModel):
    rows: list[Any]


class DbRowPatchRequest(StrictModel):
    row: dict[str, Any]


class SourceSegmentDraft(StrictModel):
    chapter: str
    name: str = ""
    segment: str
    segment_ID: str | None = None
    content: str


class PipelineStepState(StrictModel):
    name: str
    status: Literal[
        "not_started",
        "ready",
        "ready_for_skeleton",
        "running",
        "needs_review",
        "completed",
        "failed",
    ] = "not_started"
    message: str | None = None
    updated_at: datetime | None = None
    metrics: dict[str, int] = Field(default_factory=dict)


class PipelineState(StrictModel):
    volume: int = Field(ge=1)
    volume_ID: str | None = None
    steps: list[PipelineStepState] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class IDCounter(StrictModel):
    glossary_next: int = Field(default=1, ge=1)
    relationship_next: int = Field(default=1, ge=1)
    job_next: int = Field(default=1, ge=1)

    def next_value(self, key: Literal["glossary_next", "relationship_next", "job_next"]) -> int:
        value = getattr(self, key)
        setattr(self, key, value + 1)
        return value


class ProjectCreateRequest(StrictModel):
    root: str
    name: str
    genre: str = "xianxia"
    source_language: str = "zh"
    target_language: str = "vi"
    notes: str = ""


class ProjectOpenRequest(StrictModel):
    root: str


class ProjectMetadataUpdateRequest(StrictModel):
    name: str
    genre: str
    source_language: str
    target_language: str
    notes: str = ""


class ProjectCreateResponse(StrictModel):
    root: str
    metadata: ProjectMetadata
    settings: ProjectSettings


class ProjectListItem(StrictModel):
    project_ID: str
    name: str
    root: str
    genre: str
    source_language: str
    target_language: str


class ProjectHealth(StrictModel):
    volumes_imported: int = 0
    chapters_imported: int = 0
    segments_imported: int = 0
    pipeline_status_summary: dict[str, int] = Field(default_factory=dict)


class ProjectDetail(StrictModel):
    root: str
    metadata: ProjectMetadata
    settings: ProjectSettings
    health: ProjectHealth


class RegisteredProject(StrictModel):
    project_ID: str
    root: str
    name: str
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectRegistry(StrictModel):
    projects: list[RegisteredProject] = Field(default_factory=list)


class ImportManifestVolume(StrictModel):
    volume: int = Field(ge=1)
    source_file: str
    segment_file: str
    chapters: int = Field(ge=0)
    segments: int = Field(ge=0)
    validated_at: datetime
    status: Literal["ready", "failed"] = "ready"


class ImportManifest(StrictModel):
    volumes: list[ImportManifestVolume] = Field(default_factory=list)


class ImportFilePayload(StrictModel):
    filename: str
    text: str


class ImportValidateRequest(StrictModel):
    source_filename: str
    source_text: str
    segment_filename: str
    segment_text: str
    migrate_legacy_ids: bool = False


class ImportPreviewRow(StrictModel):
    volume: int
    chapter: str
    chapter_name: str
    segment_count: int
    warnings: list[str] = Field(default_factory=list)


class ImportValidationResponse(StrictModel):
    ok: bool
    volume: int | None = None
    chapters: int = 0
    segments: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preview: list[ImportPreviewRow] = Field(default_factory=list)


class ImportCommitRequest(ImportValidateRequest):
    pass


class ImportCommitResponse(StrictModel):
    validation: ImportValidationResponse
    manifest: ImportManifest
    pipeline_state: PipelineState


class PipelineItem(StrictModel):
    item_ID: str
    segment_ID: str
    chapter: str
    type: Literal["narration", "dialogue"]
    text: str
    needs_review: bool = False
    confidence: Literal["high", "low"] = "high"
    warnings: list[str] = Field(default_factory=list)


class SegmentSkeleton(StrictModel):
    segment_ID: str
    items: list[str]


class PipelineSubItem(StrictModel):
    item_ID: str
    sub_item_ID: str
    text: str


class PipelineRunResponse(StrictModel):
    volume: int
    pipeline_state: PipelineState
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


PromptTask = Literal[
    "segment_source",
    "extract_glossary",
    "extract_relationship",
    "label_dialogue",
    "translate",
]


ProviderSlot = Literal["small_llm", "big_llm"]


class PromptScope(StrictModel):
    volume: int = Field(ge=1)
    chapter: str | None = None
    segment_ID: str | None = None
    item_ID: str | None = None
    sub_item_ID: str | None = None


class PromptRenderRequest(StrictModel):
    task: PromptTask
    scope: PromptScope


class PromptRenderResponse(StrictModel):
    prompt: str
    expected_schema: str
    provider_slot: ProviderSlot


class PromptFileInfo(StrictModel):
    name: str
    path: str


class PromptFileUpdate(StrictModel):
    content: str


class PromptResultRequest(StrictModel):
    task: PromptTask
    scope: PromptScope
    result_text: str


class PromptValidationResponse(StrictModel):
    ok: bool
    expected_schema: str
    errors: list[str] = Field(default_factory=list)
    normalized: Any = None


class PromptSaveResponse(StrictModel):
    validation: PromptValidationResponse
    target_file: str
    records: int = 0


class LLMRunRequest(PromptRenderRequest):
    pass


class LLMJob(StrictModel):
    job_ID: str
    task: PromptTask
    provider_slot: ProviderSlot
    scope: PromptScope
    status: Literal["running", "completed", "failed"] = "running"
    attempts: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    error: str | None = None


class LLMRunResponse(StrictModel):
    job: LLMJob
    render: PromptRenderResponse
    result_text: str


class WorkflowVolume(StrictModel):
    volume: int
    volume_ID: str
    state: PipelineState | None = None


JsonValue = dict[str, Any] | list[Any] | str | int | float | bool | None
