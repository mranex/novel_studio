import { RefreshCcw, Save, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { apiClient, DbTableInfo, DbTableResponse, GlossaryTableName } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

const volumeTables: GlossaryTableName[] = [
  "draft_glossary",
  "glossary",
  "item_glossary",
  "segment_glossary",
  "relationships",
  "dialogue_labels",
  "translations",
  "polish_overrides"
];

export function DatabaseEditor({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [scope, setScope] = useState<"volume" | "series">("volume");
  const [volume, setVolume] = useState(1);
  const [table, setTable] = useState<GlossaryTableName | "glossary" | "relationships">("glossary");
  const [tables, setTables] = useState<DbTableInfo[]>([]);
  const [response, setResponse] = useState<DbTableResponse | null>(null);
  const [raw, setRaw] = useState("[]");
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const rows = useMemo(() => {
    const data = response?.rows ?? [];
    if (!query.trim()) {
      return data;
    }
    const needle = query.trim().toLowerCase();
    return data.filter((row) => JSON.stringify(row).toLowerCase().includes(needle));
  }, [response, query]);

  async function loadTableList() {
    if (!selectedProject) {
      return;
    }
    const result = await apiClient.listDbTables(selectedProject.project_ID);
    setTables(result.tables);
  }

  async function loadRows() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const result =
        scope === "series"
          ? await apiClient.getSeriesTable(selectedProject.project_ID, table as "glossary" | "relationships")
          : await apiClient.getVolumeTable(selectedProject.project_ID, volume, table as GlossaryTableName);
      setResponse(result);
      setRaw(JSON.stringify(result.rows, null, 2));
      await loadTableList();
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveRows() {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        setError("Raw JSON must be an array.");
        return;
      }
      const result =
        scope === "series"
          ? await apiClient.putSeriesTable(selectedProject.project_ID, table as "glossary" | "relationships", parsed)
          : await apiClient.putVolumeTable(selectedProject.project_ID, volume, table as GlossaryTableName, parsed);
      setResponse(result);
      setRaw(JSON.stringify(result.rows, null, 2));
      setMessage(result.errors.length ? "Validation returned errors. Nothing was saved." : "Table saved with backup.");
      await loadTableList();
    } catch (err) {
      setError(errorText(err));
    }
  }

  useEffect(() => {
    loadTableList().catch(() => undefined);
  }, [selectedProject?.project_ID]);

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Database Editor</span>
        <h1>Project tables</h1>
        <p>View, search, validate, and save core JSON database tables with table-level backups.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="toolbar">
        <label className="toolbar-field">
          Scope
          <select value={scope} onChange={(event) => setScope(event.target.value as "volume" | "series")}>
            <option value="volume">Volume</option>
            <option value="series">Series</option>
          </select>
        </label>
        {scope === "volume" && (
          <label className="toolbar-field">
            Volume
            <input type="number" min="1" value={volume} onChange={(event) => setVolume(Number(event.target.value || 1))} />
          </label>
        )}
        <label className="toolbar-field wide-field">
          Table
          <select value={table} onChange={(event) => setTable(event.target.value as GlossaryTableName)}>
            {(scope === "series" ? ["glossary", "relationships"] : volumeTables).map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={loadRows} disabled={!selectedProject}>
          <RefreshCcw size={18} />
          <span>Load</span>
        </button>
        <button type="button" onClick={saveRows} disabled={!selectedProject || !response}>
          <Save size={18} />
          <span>Save</span>
        </button>
      </div>

      <div className="manager-layout">
        <div className="panel">
          <h2>Tables</h2>
          <div className="result-list">
            {tables.map((item) => (
              <button
                type="button"
                className="project-card"
                key={`${item.scope}-${item.volume}-${item.name}`}
                onClick={() => {
                  setScope(item.scope);
                  if (item.volume) {
                    setVolume(item.volume);
                  }
                  setTable(item.name as GlossaryTableName);
                }}
              >
                <strong>{item.scope === "series" ? `series/${item.name}` : `volume.${String(item.volume).padStart(2, "0")}/${item.name}`}</strong>
                <span>{item.rows} rows</span>
              </button>
            ))}
          </div>
        </div>
        <div className="panel wide">
          <div className="toolbar compact">
            <label className="toolbar-field wide-field">
              Search
              <input value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <button type="button" onClick={loadRows} disabled={!selectedProject}>
              <Search size={18} />
              <span>Search loaded</span>
            </button>
          </div>
          {response?.errors.length ? <div className="notice error">{response.errors.join("; ")}</div> : null}
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Preview</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 80).map((row, index) => (
                  <tr key={index}>
                    <td>{index + 1}</td>
                    <td>
                      <code>{JSON.stringify(row)}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <label>
            Raw JSON
            <textarea className="code-editor" value={raw} onChange={(event) => setRaw(event.target.value)} />
          </label>
        </div>
      </div>
    </section>
  );
}
