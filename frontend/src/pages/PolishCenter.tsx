import { RefreshCcw, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { apiClient, PolishChapterPreview, PolishPreviewItem } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

function PolishRow({
  item,
  onSave
}: {
  item: PolishPreviewItem;
  onSave: (itemId: string, text: string) => Promise<void>;
}) {
  const [text, setText] = useState(item.preview_text);

  useEffect(() => {
    setText(item.preview_text);
  }, [item.item_ID, item.preview_text]);

  return (
    <tr>
      <td>
        <strong>{item.item_ID}</strong>
        <small>{item.type}</small>
      </td>
      <td>{item.source_text}</td>
      <td>
        <textarea value={text} onChange={(event) => setText(event.target.value)} />
      </td>
      <td>
        <span className={item.missing ? "status status-failed" : "status status-completed"}>{item.missing ? "Missing" : "Ready"}</span>
      </td>
      <td>
        <button type="button" onClick={() => onSave(item.item_ID, text)}>
          <Save size={16} />
          <span>Save</span>
        </button>
      </td>
    </tr>
  );
}

export function PolishCenter({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [volume, setVolume] = useState(1);
  const [chapter, setChapter] = useState("");
  const [preview, setPreview] = useState<PolishChapterPreview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadPreview() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const result = await apiClient.getPolishPreview(selectedProject.project_ID, volume, chapter || undefined);
      setPreview(result);
      setChapter(result.chapter);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveOverride(itemId: string, text: string) {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await apiClient.savePolishOverride(selectedProject.project_ID, volume, itemId, text);
      setMessage(`Saved override for ${itemId}.`);
      await loadPreview();
    } catch (err) {
      setError(errorText(err));
    }
  }

  useEffect(() => {
    if (selectedProject) {
      loadPreview().catch(() => undefined);
    }
  }, [selectedProject?.project_ID]);

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Polish Center</span>
        <h1>Chapter rebuild</h1>
        <p>Regenerate translated text from skeleton, translations, and per-item polish overrides.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="toolbar">
        <label className="toolbar-field">
          Volume
          <input type="number" min="1" value={volume} onChange={(event) => setVolume(Number(event.target.value || 1))} />
        </label>
        <label className="toolbar-field">
          Chapter
          <input value={chapter} onChange={(event) => setChapter(event.target.value)} placeholder="001" />
        </label>
        <button type="button" onClick={loadPreview} disabled={!selectedProject}>
          <RefreshCcw size={18} />
          <span>Load</span>
        </button>
      </div>

      {preview && (
        <>
          <div className="metric-grid">
            <div>
              <strong>{preview.items.length}</strong>
              <span>Items</span>
            </div>
            <div>
              <strong>{preview.items.filter((item) => item.missing).length}</strong>
              <span>Missing translations</span>
            </div>
            <div>
              <strong>{preview.items.filter((item) => item.polished_text).length}</strong>
              <span>Overrides</span>
            </div>
          </div>

          <div className="manager-layout">
            <div className="panel">
              <h2>{preview.chapter_name || `Chapter ${preview.chapter}`}</h2>
              <textarea className="result-editor" value={preview.text} readOnly />
            </div>
            <div className="panel wide">
              <h2>Items</h2>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Source</th>
                      <th>Polished text</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.items.map((item) => (
                      <PolishRow key={item.item_ID} item={item} onSave={saveOverride} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
