import { CheckCircle2, Play, RefreshCcw, Save, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  apiClient,
  DraftGlossaryEntry,
  GlossaryEntry,
  GlossaryMergeGroup,
  GlossaryMergeResponse,
  PipelineRunResponse
} from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

const glossaryTypes = [
  "",
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
  "other"
];

function csvToList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function GlossaryEditor({
  entry,
  onSave
}: {
  entry: GlossaryEntry;
  onSave: (entry: GlossaryEntry, changes: Partial<GlossaryEntry>) => Promise<void>;
}) {
  const [trans, setTrans] = useState(entry.trans);
  const [type, setType] = useState(entry.type);
  const [alias, setAlias] = useState(entry.alias.join(", "));
  const [link, setLink] = useState(entry.link.join(", "));
  const [humanReview, setHumanReview] = useState(entry.human_review);
  const [ready, setReady] = useState(entry.ready_for_series_update);

  useEffect(() => {
    setTrans(entry.trans);
    setType(entry.type);
    setAlias(entry.alias.join(", "));
    setLink(entry.link.join(", "));
    setHumanReview(entry.human_review);
    setReady(entry.ready_for_series_update);
  }, [entry.glossary_ID]);

  return (
    <tr>
      <td>
        <strong>{entry.source}</strong>
        <small>{entry.glossary_ID}</small>
      </td>
      <td>
        <input value={trans} onChange={(event) => setTrans(event.target.value)} />
      </td>
      <td>
        <select value={type} onChange={(event) => setType(event.target.value)}>
          {glossaryTypes.filter(Boolean).map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </td>
      <td>
        <input value={alias} onChange={(event) => setAlias(event.target.value)} />
      </td>
      <td>
        <input value={link} onChange={(event) => setLink(event.target.value)} />
      </td>
      <td>{entry.item_ID.length}</td>
      <td>{entry.segment_ID.length}</td>
      <td>
        <label className="check-label">
          <input type="checkbox" checked={humanReview} onChange={(event) => setHumanReview(event.target.checked)} />
          Review
        </label>
        <label className="check-label">
          <input type="checkbox" checked={ready} onChange={(event) => setReady(event.target.checked)} />
          Series
        </label>
      </td>
      <td>
        <button
          type="button"
          onClick={() =>
            onSave(entry, {
              trans,
              type,
              alias: csvToList(alias),
              link: csvToList(link),
              human_review: humanReview,
              ready_for_series_update: ready
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

export function GlossaryReview({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [volume, setVolume] = useState(1);
  const [draftRows, setDraftRows] = useState<DraftGlossaryEntry[]>([]);
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [groups, setGroups] = useState<GlossaryMergeGroup[]>([]);
  const [approved, setApproved] = useState<Set<string>>(new Set());
  const [typeFilter, setTypeFilter] = useState("");
  const [missingOnly, setMissingOnly] = useState(false);
  const [reviewFilter, setReviewFilter] = useState("");
  const [lastRun, setLastRun] = useState<PipelineRunResponse | null>(null);
  const [lastMerge, setLastMerge] = useState<GlossaryMergeResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const filteredGlossary = useMemo(() => {
    return glossary.filter((entry) => {
      if (typeFilter && entry.type !== typeFilter) {
        return false;
      }
      if (missingOnly && entry.trans.trim()) {
        return false;
      }
      if (reviewFilter === "reviewed" && !entry.human_review) {
        return false;
      }
      if (reviewFilter === "unreviewed" && entry.human_review) {
        return false;
      }
      return true;
    });
  }, [glossary, typeFilter, missingOnly, reviewFilter]);

  async function loadTables() {
    if (!selectedProject) {
      return;
    }
    setError(null);
    try {
      const [draftResponse, glossaryResponse] = await Promise.all([
        apiClient.getVolumeTable(selectedProject.project_ID, volume, "draft_glossary"),
        apiClient.getVolumeTable(selectedProject.project_ID, volume, "glossary")
      ]);
      setDraftRows(draftResponse.rows as DraftGlossaryEntry[]);
      setGlossary(glossaryResponse.rows as GlossaryEntry[]);
    } catch (err) {
      setError(errorText(err));
    }
  }

  useEffect(() => {
    loadTables();
  }, [selectedProject?.project_ID, volume]);

  async function runAction(action: "extract" | "merge-preview" | "merge-commit" | "scan-items" | "scan-segments") {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setRunning(action);
    setError(null);
    setMessage(null);
    try {
      if (action === "extract") {
        const response = await apiClient.runGlossaryExtract(selectedProject.project_ID, volume);
        setLastRun(response);
        setMessage("Draft glossary extraction finished.");
      }
      if (action === "merge-preview") {
        const response = await apiClient.mergeGlossary(selectedProject.project_ID, volume, {});
        setGroups(response.groups);
        setLastMerge(response);
        setMessage("Merge groups prepared.");
      }
      if (action === "merge-commit") {
        const response = await apiClient.mergeGlossary(selectedProject.project_ID, volume, {
          approved_group_keys: Array.from(approved)
        });
        setGroups(response.groups);
        setGlossary(response.glossary);
        setLastMerge(response);
        setMessage(`Committed ${response.created.length} glossary entries.`);
      }
      if (action === "scan-items") {
        const response = await apiClient.scanItemGlossary(selectedProject.project_ID, volume);
        setLastRun(response);
        setMessage("Item glossary scanner finished.");
      }
      if (action === "scan-segments") {
        const response = await apiClient.scanSegmentGlossary(selectedProject.project_ID, volume);
        setLastRun(response);
        setMessage("Segment glossary scanner finished.");
      }
      await loadTables();
    } catch (err) {
      setError(errorText(err));
    } finally {
      setRunning(null);
    }
  }

  function toggleGroup(groupKey: string) {
    const next = new Set(approved);
    if (next.has(groupKey)) {
      next.delete(groupKey);
    } else {
      next.add(groupKey);
    }
    setApproved(next);
  }

  async function saveEntry(entry: GlossaryEntry, changes: Partial<GlossaryEntry>) {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const updated = await apiClient.updateGlossaryEntry(selectedProject.project_ID, volume, entry.glossary_ID, changes);
      setGlossary(glossary.map((row) => (row.glossary_ID === updated.glossary_ID ? updated : row)));
      setMessage(`Saved ${updated.source}.`);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Glossary Pipeline</span>
        <h1>Glossary review</h1>
        <p>Extract draft terms, approve exact merge groups, edit glossary entries, then scan item and segment matches.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="toolbar">
        <label className="toolbar-field">
          Volume
          <input type="number" min="1" value={volume} onChange={(event) => setVolume(Number(event.target.value || 1))} />
        </label>
        <button type="button" onClick={loadTables} disabled={!selectedProject}>
          <RefreshCcw size={18} />
          <span>Refresh</span>
        </button>
        <button type="button" onClick={() => runAction("extract")} disabled={!selectedProject || running === "extract"}>
          <Play size={18} />
          <span>Extract Drafts</span>
        </button>
        <button type="button" onClick={() => runAction("merge-preview")} disabled={!selectedProject}>
          <Search size={18} />
          <span>Prepare Merge</span>
        </button>
        <button type="button" onClick={() => runAction("merge-commit")} disabled={!selectedProject || approved.size === 0}>
          <CheckCircle2 size={18} />
          <span>Commit Approved</span>
        </button>
        <button type="button" onClick={() => runAction("scan-items")} disabled={!selectedProject}>
          Scan Items
        </button>
        <button type="button" onClick={() => runAction("scan-segments")} disabled={!selectedProject}>
          Scan Segments
        </button>
      </div>

      <div className="metric-grid">
        <div>
          <strong>{draftRows.length}</strong>
          <span>Draft rows</span>
        </div>
        <div>
          <strong>{groups.length}</strong>
          <span>Merge groups</span>
        </div>
        <div>
          <strong>{glossary.length}</strong>
          <span>Glossary entries</span>
        </div>
        <div>
          <strong>{approved.size}</strong>
          <span>Approved groups</span>
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
        </div>
      )}

      {lastMerge && lastMerge.created.length > 0 && (
        <div className="notice success">Created: {lastMerge.created.map((entry) => entry.source).join(", ")}</div>
      )}

      <div className="manager-layout">
        <div className="panel wide">
          <h2>Merge groups</h2>
          <div className="preview-table glossary-table">
            <div className="preview-header">
              <span>Approve</span>
              <span>Source</span>
              <span>Type</span>
              <span>Count</span>
              <span>Sub-items</span>
            </div>
            {groups.map((group) => (
              <div className="preview-row" key={group.group_key}>
                <span>
                  <input type="checkbox" checked={approved.has(group.group_key)} onChange={() => toggleGroup(group.group_key)} />
                </span>
                <span>{group.source}</span>
                <span>{group.type}</span>
                <span>{group.count}</span>
                <span>{group.sub_item_ID.length}</span>
              </div>
            ))}
            {groups.length === 0 && <span className="muted">Prepare merge groups after draft glossary exists.</span>}
          </div>
        </div>

        <div className="panel wide">
          <h2>Glossary table</h2>
          <div className="toolbar compact">
            <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
              {glossaryTypes.map((item) => (
                <option key={item || "all"} value={item}>
                  {item || "All types"}
                </option>
              ))}
            </select>
            <select value={reviewFilter} onChange={(event) => setReviewFilter(event.target.value)}>
              <option value="">All review states</option>
              <option value="reviewed">Reviewed</option>
              <option value="unreviewed">Unreviewed</option>
            </select>
            <label className="check-label">
              <input type="checkbox" checked={missingOnly} onChange={(event) => setMissingOnly(event.target.checked)} />
              Missing translation
            </label>
          </div>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Trans</th>
                  <th>Type</th>
                  <th>Alias</th>
                  <th>Link</th>
                  <th>Items</th>
                  <th>Segments</th>
                  <th>Flags</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredGlossary.map((entry) => (
                  <GlossaryEditor key={entry.glossary_ID} entry={entry} onSave={saveEntry} />
                ))}
              </tbody>
            </table>
          </div>
          {filteredGlossary.length === 0 && <span className="muted">No glossary entries match the current filters.</span>}
        </div>
      </div>
    </section>
  );
}

