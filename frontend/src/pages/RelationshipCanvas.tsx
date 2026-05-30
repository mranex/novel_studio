import "@xyflow/react/dist/style.css";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseHandler,
  type OnEdgesChange,
  type OnNodesChange
} from "@xyflow/react";
import { Plus, RefreshCw, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiClient, Relationship, RelationshipCanvasResponse, RelationshipType } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

const relationshipTypes: RelationshipType[] = ["ally", "enemy", "neutral", "unknown", "love", "family"];

const edgeColors: Record<string, string> = {
  ally: "#51c2a8",
  enemy: "#f06f65",
  neutral: "#e5b84b",
  unknown: "#8c929d",
  love: "#f08fbd",
  family: "#79a7ff",
  conflict: "#ffb86b"
};

type RelationshipForm = {
  type: RelationshipType;
  relationship: string;
  pronoun: string;
  alias_pronoun: string;
  human_review: boolean;
  conflict: boolean;
  note: string;
  ready_for_series_update: boolean;
};

function timeFromKey(timeKey: string) {
  const match = /^v(\d+)_ch(\d+)_s(\d+)$/.exec(timeKey);
  if (!match) {
    return { volume: 1, chapter: 1, segment: 1, key: timeKey };
  }
  return {
    volume: Number(match[1]),
    chapter: Number(match[2]),
    segment: Number(match[3]),
    key: timeKey
  };
}

function readableTime(timeKey: string) {
  const time = timeFromKey(timeKey);
  return `Volume ${time.volume} / Chapter ${time.chapter} / Segment ${time.segment}`;
}

function relationshipToForm(relationship: Relationship | null): RelationshipForm {
  return {
    type: relationship?.type ?? "unknown",
    relationship: relationship?.relationship ?? "",
    pronoun: relationship?.pronoun ?? "",
    alias_pronoun: relationship?.alias_pronoun.join(", ") ?? "",
    human_review: relationship?.human_review ?? true,
    conflict: relationship?.conflict ?? false,
    note: relationship?.note ?? "",
    ready_for_series_update: relationship?.ready_for_series_update ?? false
  };
}

function relationshipLabel(relationship: Relationship) {
  const text = relationship.relationship || relationship.type;
  return `${relationship.speaker} -> ${relationship.listener}: ${text}`;
}

export function RelationshipCanvas({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [volume, setVolume] = useState(1);
  const [scope, setScope] = useState<"series" | "volume">("series");
  const [timeKey, setTimeKey] = useState("v01_ch001_s001");
  const [canvas, setCanvas] = useState<RelationshipCanvasResponse | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const [form, setForm] = useState<RelationshipForm>(relationshipToForm(null));
  const [addForm, setAddForm] = useState({ speaker: "", listener: "", type: "unknown" as RelationshipType, relationship: "", pronoun: "" });
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedRelationship = useMemo(
    () => canvas?.relationships.find((relationship) => relationship.relationship_ID === selectedRelationshipId) ?? null,
    [canvas, selectedRelationshipId]
  );

  const selectedTimelineIndex = useMemo(() => {
    const index = canvas?.timeline.indexOf(timeKey) ?? -1;
    return index >= 0 ? index : 0;
  }, [canvas?.timeline, timeKey]);

  function syncFlow(nextCanvas: RelationshipCanvasResponse) {
    setCanvas(nextCanvas);
    setNodes(
      nextCanvas.nodes.map((node) => ({
        id: node.id,
        position: { x: node.x ?? 0, y: node.y ?? 0 },
        data: { label: node.label },
        style: {
          border: `1px solid ${node.conflict ? edgeColors.conflict : "#343840"}`,
          background: node.conflict ? "#30251c" : "#202328",
          color: "#f0eee9",
          minWidth: 132,
          borderRadius: 6
        }
      }))
    );
    setEdges(
      nextCanvas.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label,
        type: "default",
        data: { relationships: edge.relationships, relationshipType: edge.type },
        style: { stroke: edgeColors[edge.type] ?? edgeColors.unknown, strokeWidth: edge.conflict ? 3 : 2 },
        labelStyle: { fill: "#f0eee9", fontSize: 12 },
        labelBgStyle: { fill: "#151719", fillOpacity: 0.86 },
        animated: edge.conflict
      }))
    );
    if (!addForm.speaker && nextCanvas.nodes.length >= 2) {
      setAddForm((current) => ({ ...current, speaker: nextCanvas.nodes[0].id, listener: nextCanvas.nodes[1].id }));
    }
  }

  async function loadCanvas(nextTimeKey = timeKey, nextScope = scope) {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const response = await apiClient.getRelationshipCanvas(selectedProject.project_ID, nextTimeKey, nextScope);
      syncFlow(response);
      setTimeKey(response.time_key);
    } catch (err) {
      setCanvas(null);
      setNodes([]);
      setEdges([]);
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedRelationship) {
      setForm(relationshipToForm(selectedRelationship));
    }
  }, [selectedRelationship]);

  const onNodesChange: OnNodesChange = (changes: NodeChange[]) => setNodes((current) => applyNodeChanges(changes, current));
  const onEdgesChange: OnEdgesChange = (changes: EdgeChange[]) => setEdges((current) => applyEdgeChanges(changes, current));

  const onNodeClick: NodeMouseHandler = (_event, node) => {
    const related = canvas?.relationships.find((relationship) => relationship.speaker === node.id || relationship.listener === node.id);
    setSelectedRelationshipId(related?.relationship_ID ?? null);
  };

  function onEdgeClick(edge: Edge) {
    const relationships = edge.data?.relationships as Relationship[] | undefined;
    setSelectedRelationshipId(relationships?.[0]?.relationship_ID ?? null);
  }

  async function saveRelationship() {
    if (!selectedProject || !selectedRelationship) {
      return;
    }
    setError(null);
    try {
      await apiClient.updateRelationship(selectedProject.project_ID, selectedRelationship.relationship_ID, {
        type: form.type,
        relationship: form.relationship,
        pronoun: form.pronoun || null,
        alias_pronoun: form.alias_pronoun
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        human_review: form.human_review,
        conflict: form.conflict,
        note: form.note,
        ready_for_series_update: form.ready_for_series_update
      });
      setNotice("Relationship saved.");
      await loadCanvas();
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function addRelationship() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    try {
      const created = await apiClient.createRelationship(selectedProject.project_ID, {
        speaker: addForm.speaker,
        listener: addForm.listener,
        type: addForm.type,
        relationship: addForm.relationship,
        pronoun: addForm.pronoun || null,
        alias_pronoun: [],
        time: timeFromKey(timeKey),
        source_segment_ID: timeKey,
        human_review: true,
        note: "Manual relationship"
      });
      setSelectedRelationshipId(created.relationship_ID);
      setNotice("Relationship added.");
      await loadCanvas();
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveLayout() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    try {
      await apiClient.saveRelationshipLayout(selectedProject.project_ID, {
        volume,
        nodes: nodes.map((node) => ({ id: node.id, x: node.position.x, y: node.position.y }))
      });
      setNotice("Canvas layout saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function selectTimeline(index: number) {
    const nextKey = canvas?.timeline[index];
    if (!nextKey) {
      return;
    }
    setTimeKey(nextKey);
    await loadCanvas(nextKey);
  }

  return (
    <section className="page relationship-page">
      <div className="page-heading">
        <span className="eyebrow">Relationship Canvas</span>
        <h1>Timeline graph</h1>
        <p>Review character relationship states and pronouns at the selected story point.</p>
      </div>

      <div className="toolbar compact">
        <label className="toolbar-field">
          Volume
          <input
            type="number"
            min={1}
            value={volume}
            onChange={(event) => {
              const nextVolume = Number(event.target.value) || 1;
              setVolume(nextVolume);
              setTimeKey(`v${String(nextVolume).padStart(2, "0")}_ch001_s001`);
            }}
          />
        </label>
        <label className="toolbar-field wide-field">
          Time key
          <input value={timeKey} onChange={(event) => setTimeKey(event.target.value)} />
        </label>
        <label className="toolbar-field">
          Scope
          <select value={scope} onChange={(event) => setScope(event.target.value as "series" | "volume")}>
            <option value="series">Series</option>
            <option value="volume">Volume</option>
          </select>
        </label>
        <button type="button" onClick={() => loadCanvas()} disabled={loading || !selectedProject}>
          <RefreshCw size={18} />
          <span>{loading ? "Loading" : "Load"}</span>
        </button>
        <button type="button" onClick={saveLayout} disabled={!selectedProject || nodes.length === 0}>
          <Save size={18} />
          <span>Save Layout</span>
        </button>
      </div>

      {error && <div className="notice error">{error}</div>}
      {notice && <div className="notice success">{notice}</div>}

      <div className="relationship-workspace">
        <div className="relationship-canvas-panel">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={(_event, edge) => onEdgeClick(edge)}
          >
            <Background gap={18} color="#2a2d33" />
            <MiniMap nodeColor="#51c2a8" maskColor="rgba(16, 17, 19, 0.72)" pannable zoomable />
            <Controls />
          </ReactFlow>
        </div>

        <aside className="relationship-side">
          <section className="panel">
            <span className="eyebrow">Selected time</span>
            <h2>{readableTime(timeKey)}</h2>
            <div className="timeline-control">
              <input
                type="range"
                min={0}
                max={Math.max((canvas?.timeline.length ?? 1) - 1, 0)}
                value={selectedTimelineIndex}
                onChange={(event) => selectTimeline(Number(event.target.value))}
                disabled={!canvas?.timeline.length}
              />
              <span>{canvas?.timeline[selectedTimelineIndex] ?? timeKey}</span>
            </div>
          </section>

          <section className="panel">
            <span className="eyebrow">Relationship details</span>
            {selectedRelationship ? (
              <>
                <h2>{relationshipLabel(selectedRelationship)}</h2>
                <label>
                  Type
                  <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as RelationshipType })}>
                    {relationshipTypes.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Relationship
                  <input value={form.relationship} onChange={(event) => setForm({ ...form, relationship: event.target.value })} />
                </label>
                <label>
                  Pronoun
                  <input value={form.pronoun} onChange={(event) => setForm({ ...form, pronoun: event.target.value })} />
                </label>
                <label>
                  Alias pronouns
                  <input value={form.alias_pronoun} onChange={(event) => setForm({ ...form, alias_pronoun: event.target.value })} />
                </label>
                <label>
                  Note
                  <textarea value={form.note} onChange={(event) => setForm({ ...form, note: event.target.value })} />
                </label>
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={form.conflict}
                    onChange={(event) => setForm({ ...form, conflict: event.target.checked })}
                  />
                  Conflict
                </label>
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={form.human_review}
                    onChange={(event) => setForm({ ...form, human_review: event.target.checked })}
                  />
                  Human review
                </label>
                <label className="check-label">
                  <input
                    type="checkbox"
                    checked={form.ready_for_series_update}
                    onChange={(event) => setForm({ ...form, ready_for_series_update: event.target.checked })}
                  />
                  Ready for series
                </label>
                <button type="button" onClick={saveRelationship}>
                  Save Relationship
                </button>
              </>
            ) : (
              <span className="muted">Select a node or edge to edit a relationship.</span>
            )}
          </section>

          <section className="panel">
            <span className="eyebrow">Manual add</span>
            <div className="form-grid">
              <label>
                Speaker
                <select value={addForm.speaker} onChange={(event) => setAddForm({ ...addForm, speaker: event.target.value })}>
                  {canvas?.nodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Listener
                <select value={addForm.listener} onChange={(event) => setAddForm({ ...addForm, listener: event.target.value })}>
                  {canvas?.nodes.map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="form-grid">
              <label>
                Type
                <select value={addForm.type} onChange={(event) => setAddForm({ ...addForm, type: event.target.value as RelationshipType })}>
                  {relationshipTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Pronoun
                <input value={addForm.pronoun} onChange={(event) => setAddForm({ ...addForm, pronoun: event.target.value })} />
              </label>
            </div>
            <label>
              Relationship
              <input value={addForm.relationship} onChange={(event) => setAddForm({ ...addForm, relationship: event.target.value })} />
            </label>
            <button type="button" onClick={addRelationship} disabled={!canvas?.nodes.length || !addForm.speaker || !addForm.listener}>
              <Plus size={18} />
              <span>Add Relationship</span>
            </button>
          </section>
        </aside>
      </div>
    </section>
  );
}
