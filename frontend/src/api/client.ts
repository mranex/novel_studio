export type HealthResponse = {
  status: string;
  app_version: string;
};

export type ProviderSettings = {
  base_url: string;
  api_key: string;
  model: string;
};

export type AppSettings = {
  small_llm: ProviderSettings;
  big_llm: ProviderSettings;
  batch_count: number;
  theme: "dark" | "light";
};

export type ProviderTestResponse = {
  ok: boolean;
  provider_slot: "small_llm" | "big_llm";
  message: string;
};

export type PipelineStepState = {
  name: string;
  status: "not_started" | "ready" | "ready_for_skeleton" | "running" | "needs_review" | "completed" | "failed";
  message?: string | null;
  updated_at?: string | null;
};

export type PipelineState = {
  volume: number;
  volume_ID?: string | null;
  steps: PipelineStepState[];
  updated_at: string;
};

export type WorkflowVolume = {
  volume: number;
  volume_ID: string;
  state: PipelineState | null;
};

export type WorkflowResponse = {
  volumes: WorkflowVolume[];
};

export type PipelineRunResponse = {
  volume: number;
  pipeline_state: PipelineState;
  counts: Record<string, number>;
  warnings: string[];
};

export type DraftGlossaryEntry = {
  draft_glossary_ID: string | null;
  sub_item_ID: string;
  source: string;
  type: string;
};

export type GlossaryEntry = {
  glossary_ID: string;
  volume: number | null;
  source: string;
  trans: string;
  type: string;
  alias: string[];
  human_review: boolean;
  link: string[];
  item_ID: string[];
  segment_ID: string[];
  ready_for_series_update: boolean;
};

export type DialogueLabel = {
  item_ID: string;
  segment_ID: string;
  speaker: string | null;
  listener: string | null;
  confidence: number | null;
  human_review: boolean;
  note: string;
};

export type DialogueLabelReviewItem = DialogueLabel & {
  text: string;
};

export type DialogueLabelReviewResponse = {
  volume: number;
  segment_ID: string | null;
  labels: DialogueLabelReviewItem[];
  characters: GlossaryEntry[];
  segments: string[];
};

export type ItemGlossaryEntry = {
  item_ID: string;
  glossary_ID: string[];
};

export type SegmentGlossaryEntry = {
  segment_ID: string;
  glossary_ID: string[];
};

export type TimelinePoint = {
  volume: number;
  chapter?: number | null;
  segment?: number | null;
  key?: string | null;
};

export type RelationshipType = "ally" | "enemy" | "neutral" | "unknown" | "love" | "family";

export type Relationship = {
  relationship_ID: string;
  speaker: string;
  listener: string;
  type: RelationshipType;
  relationship: string;
  pronoun: string | null;
  alias_pronoun: string[];
  time: TimelinePoint;
  source_segment_ID: string;
  human_review: boolean;
  conflict: boolean;
  note: string;
  ready_for_series_update: boolean;
};

export type RelationshipNode = {
  id: string;
  label: string;
  source: string;
  trans: string;
  conflict: boolean;
  x: number | null;
  y: number | null;
};

export type RelationshipEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string;
  conflict: boolean;
  relationships: Relationship[];
};

export type RelationshipCanvasResponse = {
  time_key: string;
  timeline: string[];
  nodes: RelationshipNode[];
  edges: RelationshipEdge[];
  relationships: Relationship[];
};

export type GlossaryTableName =
  | "draft_glossary"
  | "glossary"
  | "item_glossary"
  | "segment_glossary"
  | "relationships"
  | "dialogue_labels"
  | "translations"
  | "polish_overrides";

export type GlossaryMergeGroup = {
  group_key: string;
  source: string;
  type: string;
  draft_glossary_ID: string[];
  sub_item_ID: string[];
  count: number;
  inherited_glossary_ID: string | null;
  suggested_trans: string;
  approved: boolean;
  rejected: boolean;
};

export type GlossaryMergeResponse = {
  volume: number;
  groups: GlossaryMergeGroup[];
  created: GlossaryEntry[];
  glossary: GlossaryEntry[];
};

export type PromptTask =
  | "segment_source"
  | "extract_glossary"
  | "extract_relationship"
  | "label_dialogue"
  | "translate";

export type PromptScope = {
  volume: number;
  chapter?: string | null;
  segment_ID?: string | null;
  item_ID?: string | null;
  sub_item_ID?: string | null;
};

export type PromptRenderResponse = {
  prompt: string;
  expected_schema: string;
  provider_slot: "small_llm" | "big_llm";
};

export type PromptFileInfo = {
  name: string;
  path: string;
};

export type PromptValidationResponse = {
  ok: boolean;
  expected_schema: string;
  errors: string[];
  normalized: unknown;
};

export type PromptSaveResponse = {
  validation: PromptValidationResponse;
  target_file: string;
  records: number;
};

export type LLMRunResponse = {
  job: {
    job_ID: string;
    task: PromptTask;
    provider_slot: "small_llm" | "big_llm";
    status: "running" | "completed" | "failed";
    error: string | null;
  };
  render: PromptRenderResponse;
  result_text: string;
};

export type ProjectMetadata = {
  project_ID: string;
  name: string;
  genre: string;
  source_language: string;
  target_language: string;
  notes: string;
  created_at: string;
  app_version: string;
};

export type ProjectSettings = {
  max_subitem_tokens: number;
  batch_count_override: number | null;
  prompt_folder: string;
};

export type Translation = {
  item_ID: string;
  trans_text: string;
  updated_at: string;
};

export type TranslationJob = {
  item_ID: string;
  status: "pending" | "running" | "completed" | "failed";
  attempts: number;
  error: string | null;
  updated_at: string;
};

export type TranslationTableResponse = {
  volume: number;
  translations: Translation[];
  jobs: TranslationJob[];
};

export type PolishPreviewItem = {
  item_ID: string;
  segment_ID: string;
  type: "narration" | "dialogue";
  source_text: string;
  translation_text: string | null;
  polished_text: string | null;
  preview_text: string;
  missing: boolean;
};

export type PolishChapterPreview = {
  volume: number;
  chapter: string;
  chapter_name: string;
  text: string;
  items: PolishPreviewItem[];
};

export type ExportResponse = {
  format: string;
  scope: string;
  path: string;
  volumes: number[];
  missing_translations: number;
};

export type SeriesUpdatePreview = {
  volume: number;
  new_glossary_entries: number;
  updated_glossary_entries: number;
  inherited_glossary_entries: number;
  new_relationship_timestamps: number;
  skipped_duplicate_relationship_states: number;
  conflicts_needing_review: number;
  glossary_changes: unknown[];
  relationship_changes: unknown[];
};

export type SeriesUpdateResponse = {
  preview: SeriesUpdatePreview;
  series_glossary_rows: number;
  series_relationship_rows: number;
  backups: string[];
};

export type DbTableInfo = {
  scope: "volume" | "series";
  name: string;
  volume: number | null;
  path: string;
  rows: number;
};

export type DbTableResponse = {
  scope: "volume" | "series";
  table: string;
  volume: number | null;
  rows: unknown[];
  errors: string[];
};

export type ProjectHealth = {
  volumes_imported: number;
  chapters_imported: number;
  segments_imported: number;
  pipeline_status_summary: Record<string, number>;
};

export type ProjectDetail = {
  root: string;
  metadata: ProjectMetadata;
  settings: ProjectSettings;
  health: ProjectHealth;
};

export type ProjectCreateResponse = {
  root: string;
  metadata: ProjectMetadata;
  settings: ProjectSettings;
};

export type ProjectListItem = {
  project_ID: string;
  name: string;
  root: string;
  genre: string;
  source_language: string;
  target_language: string;
};

export type ImportPreviewRow = {
  volume: number;
  chapter: string;
  chapter_name: string;
  segment_count: number;
  warnings: string[];
};

export type ImportValidationResponse = {
  ok: boolean;
  volume: number | null;
  chapters: number;
  segments: number;
  errors: string[];
  warnings: string[];
  preview: ImportPreviewRow[];
};

export type ImportManifestVolume = {
  volume: number;
  source_file: string;
  segment_file: string;
  chapters: number;
  segments: number;
  validated_at: string;
  status: "ready" | "failed";
};

export type ImportManifest = {
  volumes: ImportManifestVolume[];
};

export type ImportCommitResponse = {
  validation: ImportValidationResponse;
  manifest: ImportManifest;
  pipeline_state: PipelineState;
};

const API_BASE = "/api";

function detailMessage(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }
  if (detail && typeof detail === "object" && "detail" in detail) {
    const nested = (detail as { detail: unknown }).detail;
    if (typeof nested === "string" && nested.trim()) {
      return nested.trim();
    }
    if (Array.isArray(nested)) {
      return nested
        .map((item) => (typeof item === "object" && item && "msg" in item ? String((item as { msg: unknown }).msg) : String(item)))
        .join("; ");
    }
  }
  return `Request failed with ${status}`;
}

async function readErrorDetail(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  const text = await response.text();
  if (!text.trim() || text.trimStart().startsWith("<")) {
    return null;
  }
  return text;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(detailMessage(detail, status));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorDetail(response));
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  health: () => request<HealthResponse>("/health"),
  getSettings: () => request<{ app: AppSettings }>("/settings"),
  updateSettings: (body: AppSettings) =>
    request<AppSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(body)
    }),
  testProvider: (provider_slot: "small_llm" | "big_llm") =>
    request<ProviderTestResponse>("/settings/test", {
      method: "POST",
      body: JSON.stringify({ provider_slot })
    }),
  listProjects: () => request<{ projects: ProjectListItem[] }>("/projects"),
  createProject: (body: {
    root: string;
    name: string;
    genre: string;
    source_language: string;
    target_language: string;
    notes: string;
  }) =>
    request<ProjectCreateResponse>("/projects", {
      method: "POST",
      body: JSON.stringify(body)
    }),
  openProject: (root: string) =>
    request<ProjectCreateResponse>("/projects/open", {
      method: "POST",
      body: JSON.stringify({ root })
    }),
  getProject: (projectId: string) => request<ProjectDetail>(`/projects/${encodeURIComponent(projectId)}`),
  updateMetadata: (
    projectId: string,
    body: {
      name: string;
      genre: string;
      source_language: string;
      target_language: string;
      notes: string;
    }
  ) =>
    request<ProjectDetail>(`/projects/${encodeURIComponent(projectId)}/metadata`, {
      method: "PUT",
      body: JSON.stringify(body)
    }),
  updateProjectSettings: (projectId: string, body: ProjectSettings) =>
    request<ProjectSettings>(`/projects/${encodeURIComponent(projectId)}/settings`, {
      method: "PUT",
      body: JSON.stringify(body)
    }),
  validateImport: (
    projectId: string,
    body: {
      source_filename: string;
      source_text: string;
      segment_filename: string;
      segment_text: string;
      migrate_legacy_ids?: boolean;
    }
  ) =>
    request<ImportValidationResponse>(`/projects/${encodeURIComponent(projectId)}/import/validate`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  commitImport: (
    projectId: string,
    body: {
      source_filename: string;
      source_text: string;
      segment_filename: string;
      segment_text: string;
      migrate_legacy_ids?: boolean;
    }
  ) =>
    request<ImportCommitResponse>(`/projects/${encodeURIComponent(projectId)}/import/commit`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  getManifest: (projectId: string) =>
    request<ImportManifest>(`/projects/${encodeURIComponent(projectId)}/import/manifest`),
  runSkeleton: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/skeleton`, {
      method: "POST"
    }),
  runSubitems: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/subitems`, {
      method: "POST"
    }),
  runGlossaryExtract: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/glossary/extract`, {
      method: "POST"
    }),
  mergeGlossary: (projectId: string, volume: number, body: { approved_group_keys?: string[]; rejected_group_keys?: string[] }) =>
    request<GlossaryMergeResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/glossary/merge`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  scanItemGlossary: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/glossary/scan-items`, {
      method: "POST"
    }),
  scanSegmentGlossary: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/glossary/scan-segments`, {
      method: "POST"
    }),
  runRelationshipExtract: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/relationships/extract`, {
      method: "POST"
    }),
  mergeRelationships: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/relationships/merge`, {
      method: "POST"
    }),
  runDialogueLabelExtract: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/dialogue-labels/extract`, {
      method: "POST"
    }),
  runTranslate: (projectId: string, volume: number, body: { item_ID?: string[]; overwrite?: boolean } = {}) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/translate`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  retryFailedTranslations: (projectId: string, volume: number) =>
    request<PipelineRunResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/translate/retry-failed`, {
      method: "POST"
    }),
  getTranslations: (projectId: string, volume: number) =>
    request<TranslationTableResponse>(`/projects/${encodeURIComponent(projectId)}/translations?volume=${volume}`),
  updateTranslation: (projectId: string, volume: number, itemId: string, trans_text: string) =>
    request<Translation>(`/projects/${encodeURIComponent(projectId)}/translations/${encodeURIComponent(itemId)}?volume=${volume}`, {
      method: "PATCH",
      body: JSON.stringify({ trans_text })
    }),
  previewSeriesUpdate: (projectId: string, volume: number) =>
    request<SeriesUpdatePreview>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/series/preview`, {
      method: "POST"
    }),
  applySeriesUpdate: (projectId: string, volume: number) =>
    request<SeriesUpdateResponse>(`/projects/${encodeURIComponent(projectId)}/pipeline/${volume}/series/update`, {
      method: "POST"
    }),
  getVolumeTable: (projectId: string, volume: number, table: GlossaryTableName) =>
    request<DbTableResponse>(
      `/projects/${encodeURIComponent(projectId)}/db/volumes/${volume}/${table}`
    ),
  listDbTables: (projectId: string) => request<{ tables: DbTableInfo[] }>(`/projects/${encodeURIComponent(projectId)}/db/tables`),
  getSeriesTable: (projectId: string, table: "glossary" | "relationships") =>
    request<DbTableResponse>(`/projects/${encodeURIComponent(projectId)}/db/series/${table}`),
  putVolumeTable: (projectId: string, volume: number, table: GlossaryTableName, rows: unknown[]) =>
    request<DbTableResponse>(`/projects/${encodeURIComponent(projectId)}/db/volumes/${volume}/${table}`, {
      method: "PUT",
      body: JSON.stringify({ rows })
    }),
  putSeriesTable: (projectId: string, table: "glossary" | "relationships", rows: unknown[]) =>
    request<DbTableResponse>(`/projects/${encodeURIComponent(projectId)}/db/series/${table}`, {
      method: "PUT",
      body: JSON.stringify({ rows })
    }),
  updateGlossaryEntry: (
    projectId: string,
    volume: number,
    glossaryId: string,
    body: Partial<Pick<GlossaryEntry, "trans" | "type" | "alias" | "link" | "human_review" | "ready_for_series_update">>
  ) =>
    request<GlossaryEntry>(`/projects/${encodeURIComponent(projectId)}/db/volumes/${volume}/glossary/${encodeURIComponent(glossaryId)}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    }),
  getRelationshipCanvas: (projectId: string, timeKey: string, scope: "series" | "volume" = "series") =>
    request<RelationshipCanvasResponse>(
      `/projects/${encodeURIComponent(projectId)}/relationships/canvas?time_key=${encodeURIComponent(timeKey)}&scope=${encodeURIComponent(scope)}`
    ),
  updateRelationship: (
    projectId: string,
    relationshipId: string,
    body: Partial<
      Pick<
        Relationship,
        "type" | "relationship" | "pronoun" | "alias_pronoun" | "human_review" | "conflict" | "note" | "ready_for_series_update"
      >
    >
  ) =>
    request<Relationship>(`/projects/${encodeURIComponent(projectId)}/relationships/${encodeURIComponent(relationshipId)}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    }),
  createRelationship: (
    projectId: string,
    body: {
      speaker: string;
      listener: string;
      type: RelationshipType;
      relationship: string;
      pronoun?: string | null;
      alias_pronoun?: string[];
      time: TimelinePoint;
      source_segment_ID: string;
      human_review?: boolean;
      conflict?: boolean;
      note?: string;
    }
  ) =>
    request<Relationship>(`/projects/${encodeURIComponent(projectId)}/relationships`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  saveRelationshipLayout: (projectId: string, body: { volume: number; nodes: { id: string; x: number; y: number }[] }) =>
    request<{ nodes: number }>(`/projects/${encodeURIComponent(projectId)}/relationships/layout`, {
      method: "PUT",
      body: JSON.stringify(body)
    }),
  getDialogueLabels: (projectId: string, volume: number, segmentId?: string) =>
    request<DialogueLabelReviewResponse>(
      `/projects/${encodeURIComponent(projectId)}/dialogue-labels?volume=${volume}${
        segmentId ? `&segment_ID=${encodeURIComponent(segmentId)}` : ""
      }`
    ),
  updateDialogueLabel: (
    projectId: string,
    itemId: string,
    body: Partial<Pick<DialogueLabel, "speaker" | "listener" | "confidence" | "human_review" | "note">>
  ) =>
    request<DialogueLabel>(`/projects/${encodeURIComponent(projectId)}/dialogue-labels/${encodeURIComponent(itemId)}`, {
      method: "PATCH",
      body: JSON.stringify(body)
    }),
  listPrompts: (projectId: string) => request<{ prompts: PromptFileInfo[] }>(`/projects/${encodeURIComponent(projectId)}/prompts`),
  getPrompt: (projectId: string, name: string) =>
    request<{ name: string; content: string }>(`/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(name)}`),
  updatePrompt: (projectId: string, name: string, content: string) =>
    request<{ name: string; content: string }>(`/projects/${encodeURIComponent(projectId)}/prompts/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify({ content })
    }),
  renderPrompt: (projectId: string, body: { task: PromptTask; scope: PromptScope }) =>
    request<PromptRenderResponse>(`/projects/${encodeURIComponent(projectId)}/prompts/render`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  runLLM: (projectId: string, body: { task: PromptTask; scope: PromptScope }) =>
    request<LLMRunResponse>(`/projects/${encodeURIComponent(projectId)}/llm/run`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  validatePromptResult: (projectId: string, body: { task: PromptTask; scope: PromptScope; result_text: string }) =>
    request<PromptValidationResponse>(`/projects/${encodeURIComponent(projectId)}/prompts/validate-result`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  savePromptResult: (projectId: string, body: { task: PromptTask; scope: PromptScope; result_text: string }) =>
    request<PromptSaveResponse>(`/projects/${encodeURIComponent(projectId)}/prompts/save-result`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  getPolishPreview: (projectId: string, volume: number, chapter?: string) =>
    request<PolishChapterPreview>(
      `/projects/${encodeURIComponent(projectId)}/polish/preview?volume=${volume}${chapter ? `&chapter=${encodeURIComponent(chapter)}` : ""}`
    ),
  savePolishOverride: (projectId: string, volume: number, itemId: string, text: string) =>
    request<{ item_ID: string; text: string; updated_at: string }>(
      `/projects/${encodeURIComponent(projectId)}/polish/${encodeURIComponent(itemId)}?volume=${volume}`,
      {
        method: "PATCH",
        body: JSON.stringify({ text })
      }
    ),
  exportProject: (projectId: string, body: { format: "txt" | "md" | "html"; scope: "volume" | "selected_volumes" | "series"; volumes: number[] }) =>
    request<ExportResponse>(`/projects/${encodeURIComponent(projectId)}/export`, {
      method: "POST",
      body: JSON.stringify(body)
    }),
  workflow: (projectRoot: string) =>
    request<WorkflowResponse>(`/projects/workflow?project_root=${encodeURIComponent(projectRoot)}`)
};
