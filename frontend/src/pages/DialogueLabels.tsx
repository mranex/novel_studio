import { Play, RefreshCcw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiClient, DialogueLabelReviewItem, GlossaryEntry, PipelineRunResponse } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

function characterLabel(entry: GlossaryEntry) {
  const alias = entry.alias.length ? ` / ${entry.alias.join(", ")}` : "";
  const name = entry.trans || entry.source;
  return `${name} (${entry.source}${alias})`;
}

function DialogueRow({
  row,
  characters,
  onSave
}: {
  row: DialogueLabelReviewItem;
  characters: GlossaryEntry[];
  onSave: (row: DialogueLabelReviewItem, changes: Partial<DialogueLabelReviewItem>) => Promise<void>;
}) {
  const [speaker, setSpeaker] = useState(row.speaker ?? "");
  const [listener, setListener] = useState(row.listener ?? "");
  const [confidence, setConfidence] = useState(row.confidence?.toString() ?? "");
  const [humanReview, setHumanReview] = useState(row.human_review);
  const [note, setNote] = useState(row.note);

  useEffect(() => {
    setSpeaker(row.speaker ?? "");
    setListener(row.listener ?? "");
    setConfidence(row.confidence?.toString() ?? "");
    setHumanReview(row.human_review);
    setNote(row.note);
  }, [row.item_ID, row.speaker, row.listener, row.confidence, row.human_review, row.note]);

  const options = [
    <option key="unknown" value="">
      Unknown
    </option>,
    ...characters.map((entry) => (
      <option key={entry.glossary_ID} value={entry.glossary_ID}>
        {characterLabel(entry)}
      </option>
    ))
  ];

  return (
    <tr>
      <td>
        <strong>{row.item_ID}</strong>
        <small>{row.segment_ID}</small>
      </td>
      <td>{row.text}</td>
      <td>
        <select value={speaker} onChange={(event) => setSpeaker(event.target.value)}>
          {options}
        </select>
      </td>
      <td>
        <select value={listener} onChange={(event) => setListener(event.target.value)}>
          {options}
        </select>
      </td>
      <td>
        <input
          type="number"
          min={0}
          max={1}
          step={0.01}
          value={confidence}
          onChange={(event) => setConfidence(event.target.value)}
        />
      </td>
      <td>
        <label className="check-label">
          <input type="checkbox" checked={humanReview} onChange={(event) => setHumanReview(event.target.checked)} />
          Review
        </label>
      </td>
      <td>
        <input value={note} onChange={(event) => setNote(event.target.value)} />
      </td>
      <td>
        <button
          type="button"
          onClick={() =>
            onSave(row, {
              speaker: speaker || null,
              listener: listener || null,
              confidence: confidence.trim() ? Number(confidence) : null,
              human_review: humanReview,
              note
            })
          }
        >
          <Save size={16} />
          <span>Save</span>
        </button>
      </td>
    </tr>
  );
}

export function DialogueLabels({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [volume, setVolume] = useState(1);
  const [segmentId, setSegmentId] = useState("");
  const [labels, setLabels] = useState<DialogueLabelReviewItem[]>([]);
  const [characters, setCharacters] = useState<GlossaryEntry[]>([]);
  const [segments, setSegments] = useState<string[]>([]);
  const [reviewOnly, setReviewOnly] = useState(false);
  const [lastRun, setLastRun] = useState<PipelineRunResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const filteredLabels = useMemo(
    () => labels.filter((row) => !reviewOnly || row.human_review || row.speaker === null || row.listener === null),
    [labels, reviewOnly]
  );

  async function loadLabels(nextSegment = segmentId) {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    try {
      const response = await apiClient.getDialogueLabels(selectedProject.project_ID, volume, nextSegment || undefined);
      setLabels(response.labels);
      setCharacters(response.characters.filter((entry) => entry.type === "character"));
      setSegments(response.segments);
      if (!nextSegment && response.segments.length > 0) {
        setSegmentId(response.segments[0]);
      }
    } catch (err) {
      setLabels([]);
      setCharacters([]);
      setSegments([]);
      setError(errorText(err));
    }
  }

  useEffect(() => {
    if (selectedProject) {
      loadLabels("");
    }
  }, [selectedProject?.project_ID, volume]);

  async function runExtract() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setRunning(true);
    setMessage(null);
    setError(null);
    try {
      const response = await apiClient.runDialogueLabelExtract(selectedProject.project_ID, volume);
      setLastRun(response);
      setMessage("Dialogue labeling finished.");
      await loadLabels(segmentId);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setRunning(false);
    }
  }

  async function saveLabel(row: DialogueLabelReviewItem, changes: Partial<DialogueLabelReviewItem>) {
    if (!selectedProject) {
      return;
    }
    setMessage(null);
    setError(null);
    try {
      const updated = await apiClient.updateDialogueLabel(selectedProject.project_ID, row.item_ID, changes);
      setLabels(labels.map((label) => (label.item_ID === updated.item_ID ? { ...label, ...updated, text: label.text } : label)));
      setMessage(`Saved ${updated.item_ID}.`);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Dialogue Label Pipeline</span>
        <h1>Dialogue labels</h1>
        <p>Review speaker and listener labels for dialogue items without depending on relationship data.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="toolbar compact">
        <label className="toolbar-field">
          Volume
          <input type="number" min={1} value={volume} onChange={(event) => setVolume(Number(event.target.value || 1))} />
        </label>
        <label className="toolbar-field wide-field">
          Segment
          <select
            value={segmentId}
            onChange={(event) => {
              setSegmentId(event.target.value);
              loadLabels(event.target.value);
            }}
          >
            <option value="">All segments</option>
            {segments.map((segment) => (
              <option key={segment} value={segment}>
                {segment}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={() => loadLabels(segmentId)} disabled={!selectedProject}>
          <RefreshCcw size={18} />
          <span>Refresh</span>
        </button>
        <button type="button" onClick={runExtract} disabled={!selectedProject || running}>
          <Play size={18} />
          <span>{running ? "Running" : "Run Labels"}</span>
        </button>
        <label className="check-label">
          <input type="checkbox" checked={reviewOnly} onChange={(event) => setReviewOnly(event.target.checked)} />
          Needs review
        </label>
      </div>

      <div className="metric-grid">
        <div>
          <strong>{labels.length}</strong>
          <span>Dialogue rows</span>
        </div>
        <div>
          <strong>{labels.filter((row) => row.human_review).length}</strong>
          <span>Needs review</span>
        </div>
        <div>
          <strong>{characters.length}</strong>
          <span>Characters</span>
        </div>
        <div>
          <strong>{segments.length}</strong>
          <span>Segments</span>
        </div>
      </div>

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

      <div className="panel wide">
        <h2>Dialogue items</h2>
        <div className="table-scroll">
          <table className="data-table dialogue-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Dialogue</th>
                <th>Speaker</th>
                <th>Listener</th>
                <th>Confidence</th>
                <th>Flags</th>
                <th>Note</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredLabels.map((row) => (
                <DialogueRow key={row.item_ID} row={row} characters={characters} onSave={saveLabel} />
              ))}
            </tbody>
          </table>
        </div>
        {filteredLabels.length === 0 && <span className="muted">No dialogue labels match the current filters.</span>}
      </div>
    </section>
  );
}
