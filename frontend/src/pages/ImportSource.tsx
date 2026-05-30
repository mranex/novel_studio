import { CheckCircle2, Save, Upload } from "lucide-react";
import { useState } from "react";

import { apiClient, ImportValidationResponse } from "../api/client";
import type { ImportFileState, SelectedProject } from "../types";
import { errorText, readImportFile } from "../utils";

export function ImportSource({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [sourceFile, setSourceFile] = useState<ImportFileState | null>(null);
  const [segmentFile, setSegmentFile] = useState<ImportFileState | null>(null);
  const [validation, setValidation] = useState<ImportValidationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function chooseSource(file: File | undefined) {
    if (file) {
      setSourceFile(await readImportFile(file));
      setValidation(null);
    }
  }

  async function chooseSegment(file: File | undefined) {
    if (file) {
      setSegmentFile(await readImportFile(file));
      setValidation(null);
    }
  }

  function payload() {
    if (!sourceFile || !segmentFile) {
      throw new Error("Choose both source and segment JSON files.");
    }
    return {
      source_filename: sourceFile.filename,
      source_text: sourceFile.text,
      segment_filename: segmentFile.filename,
      segment_text: segmentFile.text
    };
  }

  async function validate() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.validateImport(selectedProject.project_ID, payload());
      setValidation(response);
      setMessage(response.ok ? "Validation passed." : "Validation found errors.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function commit() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.commitImport(selectedProject.project_ID, payload());
      setValidation(response.validation);
      setMessage("Import saved and pipeline is ready for skeleton.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Import Source</span>
        <h1>Source and segments</h1>
        <p>Validate exported files from the Source Preparer before copying them into the current project.</p>
      </div>

      {!selectedProject && <div className="notice error">Select a project in Project Manager first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="import-grid">
        <label className="file-zone">
          <Upload size={24} />
          <strong>Source volume JSON</strong>
          <span>{sourceFile?.filename ?? "Choose volume.XX.json"}</span>
          <input type="file" accept=".json,application/json" onChange={(event) => chooseSource(event.target.files?.[0])} />
        </label>
        <label className="file-zone">
          <Upload size={24} />
          <strong>Segment JSON</strong>
          <span>{segmentFile?.filename ?? "Choose volume.XX.segment.json"}</span>
          <input type="file" accept=".json,application/json" onChange={(event) => chooseSegment(event.target.files?.[0])} />
        </label>
      </div>

      <div className="toolbar compact">
        <button type="button" onClick={validate} disabled={!selectedProject || !sourceFile || !segmentFile}>
          <CheckCircle2 size={18} />
          <span>Validate</span>
        </button>
        <button type="button" onClick={commit} disabled={!selectedProject || !validation?.ok}>
          <Save size={18} />
          <span>Confirm Import</span>
        </button>
      </div>

      {validation && (
        <div className="panel">
          <h2>Validation results</h2>
          <div className="metric-grid">
            <div>
              <strong>{validation.volume ?? "-"}</strong>
              <span>Volume</span>
            </div>
            <div>
              <strong>{validation.chapters}</strong>
              <span>Chapters</span>
            </div>
            <div>
              <strong>{validation.segments}</strong>
              <span>Segments</span>
            </div>
          </div>
          {validation.errors.length > 0 && (
            <div className="result-list error-text">
              {validation.errors.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          )}
          {validation.warnings.length > 0 && (
            <div className="result-list warning-text">
              {validation.warnings.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          )}
          <div className="preview-table">
            <div className="preview-header">
              <span>Volume</span>
              <span>Chapter</span>
              <span>Segments</span>
              <span>Warnings</span>
            </div>
            {validation.preview.map((row) => (
              <div className="preview-row" key={`${row.volume}-${row.chapter}`}>
                <span>{row.volume}</span>
                <span>
                  {row.chapter} - {row.chapter_name || "Untitled"}
                </span>
                <span>{row.segment_count}</span>
                <span>{row.warnings.length}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

