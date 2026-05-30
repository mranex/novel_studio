import { FileDown } from "lucide-react";
import { useState } from "react";

import { apiClient, ExportResponse } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

function parseVolumes(value: string): number[] {
  return value
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0);
}

export function ExportPage({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [format, setFormat] = useState<"txt" | "md" | "html">("md");
  const [scope, setScope] = useState<"volume" | "selected_volumes" | "series">("volume");
  const [volumes, setVolumes] = useState("1");
  const [result, setResult] = useState<ExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runExport() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setResult(null);
    try {
      const response = await apiClient.exportProject(selectedProject.project_ID, {
        format,
        scope,
        volumes: parseVolumes(volumes)
      });
      setResult(response);
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Export</span>
        <h1>Readable output</h1>
        <p>Export rebuilt polished text without mutating series glossary or relationship files.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {result && (
        <div className={result.missing_translations ? "notice error" : "notice success"}>
          Exported {result.format.toUpperCase()} to {result.path}. Missing translations: {result.missing_translations}.
        </div>
      )}

      <div className="panel">
        <div className="form-grid">
          <label>
            Format
            <select value={format} onChange={(event) => setFormat(event.target.value as "txt" | "md" | "html")}>
              <option value="md">Markdown</option>
              <option value="txt">TXT</option>
              <option value="html">HTML</option>
            </select>
          </label>
          <label>
            Scope
            <select value={scope} onChange={(event) => setScope(event.target.value as "volume" | "selected_volumes" | "series")}>
              <option value="volume">One volume</option>
              <option value="selected_volumes">Selected volumes</option>
              <option value="series">Full series</option>
            </select>
          </label>
          <label>
            Volumes
            <input value={volumes} onChange={(event) => setVolumes(event.target.value)} placeholder="1, 2" />
          </label>
        </div>
        <button type="button" onClick={runExport} disabled={!selectedProject}>
          <FileDown size={18} />
          <span>Export</span>
        </button>
      </div>
    </section>
  );
}
