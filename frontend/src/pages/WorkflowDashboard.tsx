import { LayoutDashboard, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

import { apiClient, PipelineRunResponse, WorkflowVolume } from "../api/client";
import { statusLabels } from "../appData";
import type { SelectedProject } from "../types";
import { classForStatus, errorText } from "../utils";

export function WorkflowDashboard({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [projectRoot, setProjectRoot] = useState(selectedProject?.root ?? "");
  const [volumes, setVolumes] = useState<WorkflowVolume[]>([]);
  const [lastRun, setLastRun] = useState<PipelineRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [runningAction, setRunningAction] = useState<string | null>(null);

  useEffect(() => {
    if (selectedProject?.root) {
      setProjectRoot(selectedProject.root);
    }
  }, [selectedProject?.root]);

  async function loadWorkflow() {
    if (!projectRoot.trim()) {
      setError("Enter a project folder path.");
      setVolumes([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.workflow(projectRoot.trim());
      setVolumes(response.volumes);
    } catch (err) {
      setVolumes([]);
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }

  async function runPipelineAction(
    volume: number,
    action:
      | "skeleton"
      | "subitems"
      | "glossary-extract"
      | "glossary-scan-items"
      | "glossary-scan-segments"
      | "relationships-extract"
      | "relationships-merge"
      | "dialogue-labels-extract"
      | "translate"
      | "translate-retry"
      | "series-preview"
      | "series-update"
  ) {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setRunningAction(`${action}-${volume}`);
    try {
      const volumeRecord = volumes.find((item) => item.volume === volume);
      const response =
        action === "skeleton"
          ? await apiClient.runSkeleton(selectedProject.project_ID, volume)
          : action === "subitems"
            ? await apiClient.runSubitems(selectedProject.project_ID, volume)
            : action === "glossary-extract"
              ? await apiClient.runGlossaryExtract(selectedProject.project_ID, volume)
              : action === "glossary-scan-items"
                ? await apiClient.scanItemGlossary(selectedProject.project_ID, volume)
                : action === "glossary-scan-segments"
                  ? await apiClient.scanSegmentGlossary(selectedProject.project_ID, volume)
                  : action === "relationships-extract"
                    ? await apiClient.runRelationshipExtract(selectedProject.project_ID, volume)
                    : action === "relationships-merge"
                      ? await apiClient.mergeRelationships(selectedProject.project_ID, volume)
                      : action === "dialogue-labels-extract"
                        ? await apiClient.runDialogueLabelExtract(selectedProject.project_ID, volume)
                        : action === "translate"
                          ? await apiClient.runTranslate(selectedProject.project_ID, volume)
                          : action === "translate-retry"
                            ? await apiClient.retryFailedTranslations(selectedProject.project_ID, volume)
                            : action === "series-preview"
                              ? ({
                                  volume,
                                  pipeline_state: volumeRecord?.state ?? { volume, volume_ID: `v${String(volume).padStart(2, "0")}`, steps: [], updated_at: "" },
                                  counts: await apiClient
                                    .previewSeriesUpdate(selectedProject.project_ID, volume)
                                    .then((preview) => ({
                                      new_glossary_entries: preview.new_glossary_entries,
                                      updated_glossary_entries: preview.updated_glossary_entries,
                                      new_relationship_timestamps: preview.new_relationship_timestamps,
                                      conflicts_needing_review: preview.conflicts_needing_review
                                    })),
                                  warnings: []
                                } as PipelineRunResponse)
                              : ({
                                  volume,
                                  pipeline_state: volumeRecord?.state ?? { volume, volume_ID: `v${String(volume).padStart(2, "0")}`, steps: [], updated_at: "" },
                                  counts: await apiClient.applySeriesUpdate(selectedProject.project_ID, volume).then((response) => ({
                                    series_glossary_rows: response.series_glossary_rows,
                                    series_relationship_rows: response.series_relationship_rows,
                                    backups: response.backups.length
                                  })),
                                  warnings: []
                                } as PipelineRunResponse);
      setLastRun(response);
      await loadWorkflow();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setRunningAction(null);
    }
  }

  const hasVolumes = volumes.length > 0;

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Workflow Dashboard</span>
        <h1>Volume pipeline</h1>
        <p>Load pipeline state files from a local project folder.</p>
      </div>

      <div className="toolbar">
        <input
          aria-label="Project folder path"
          placeholder="C:\\Novels\\My Project"
          value={projectRoot}
          onChange={(event) => setProjectRoot(event.target.value)}
        />
        <button type="button" onClick={loadWorkflow} disabled={loading}>
          <LayoutDashboard size={18} />
          <span>{loading ? "Loading" : "Load"}</span>
        </button>
      </div>

      {error && <div className="notice error">{error}</div>}
      {lastRun && (
        <div className="panel">
          <h2>Last pipeline run</h2>
          <div className="metric-grid">
            {Object.entries(lastRun.counts).map(([key, value]) => (
              <div key={key}>
                <strong>{value}</strong>
                <span>{key.replace(/_/g, " ")}</span>
              </div>
            ))}
          </div>
          {lastRun.warnings.length > 0 && (
            <div className="result-list warning-text">
              {lastRun.warnings.map((warning) => (
                <span key={warning}>{warning}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="volume-grid">
        {hasVolumes ? (
          volumes.map((volume) => (
            <article className="volume-card" key={volume.volume_ID}>
              <div className="volume-card-header">
                <div>
                  <span className="eyebrow">Volume {volume.volume}</span>
                  <h2>{volume.volume_ID}</h2>
                </div>
              </div>
              <div className="pipeline-actions">
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "skeleton")}
                  disabled={!selectedProject || runningAction === `skeleton-${volume.volume}`}
                >
                  Build Skeleton
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "subitems")}
                  disabled={!selectedProject || runningAction === `subitems-${volume.volume}`}
                >
                  Split Sub-items
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "glossary-extract")}
                  disabled={!selectedProject || runningAction === `glossary-extract-${volume.volume}`}
                >
                  Extract Glossary
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "glossary-scan-items")}
                  disabled={!selectedProject || runningAction === `glossary-scan-items-${volume.volume}`}
                >
                  Scan Items
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "glossary-scan-segments")}
                  disabled={!selectedProject || runningAction === `glossary-scan-segments-${volume.volume}`}
                >
                  Scan Segments
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "relationships-extract")}
                  disabled={!selectedProject || runningAction === `relationships-extract-${volume.volume}`}
                >
                  Extract Relationships
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "relationships-merge")}
                  disabled={!selectedProject || runningAction === `relationships-merge-${volume.volume}`}
                >
                  Merge Relationships
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "dialogue-labels-extract")}
                  disabled={!selectedProject || runningAction === `dialogue-labels-extract-${volume.volume}`}
                >
                  Label Dialogue
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "translate")}
                  disabled={!selectedProject || runningAction === `translate-${volume.volume}`}
                >
                  Translate
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "translate-retry")}
                  disabled={!selectedProject || runningAction === `translate-retry-${volume.volume}`}
                >
                  Retry Failed
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "series-preview")}
                  disabled={!selectedProject || runningAction === `series-preview-${volume.volume}`}
                >
                  Preview Series
                </button>
                <button
                  type="button"
                  onClick={() => runPipelineAction(volume.volume, "series-update")}
                  disabled={!selectedProject || runningAction === `series-update-${volume.volume}`}
                >
                  Apply Series
                </button>
              </div>
              <div className="step-list">
                {(volume.state?.steps ?? []).map((step) => (
                  <div className="step-row" key={step.name}>
                    <span>
                      {step.name}
                      {step.message && <small>{step.message}</small>}
                    </span>
                    <span className={classForStatus(step.status)}>
                      {statusLabels[step.status] ?? step.status}
                    </span>
                  </div>
                ))}
                {volume.state?.steps.length === 0 && <span className="muted">No steps recorded.</span>}
              </div>
            </article>
          ))
        ) : (
          <div className="empty-panel">
            <Workflow size={32} />
            <span>No pipeline state loaded.</span>
          </div>
        )}
      </div>
    </section>
  );
}
