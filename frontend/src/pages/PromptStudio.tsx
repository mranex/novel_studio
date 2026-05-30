import { CheckCircle2, Clipboard, Play, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import {
  apiClient,
  PromptFileInfo,
  PromptRenderResponse,
  PromptScope,
  PromptTask,
  PromptValidationResponse
} from "../api/client";
import { promptTaskLabels } from "../appData";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

export function PromptStudio({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [task, setTask] = useState<PromptTask>("extract_glossary");
  const [scope, setScope] = useState<PromptScope>({ volume: 1, segment_ID: "", item_ID: "", sub_item_ID: "" });
  const [prompts, setPrompts] = useState<PromptFileInfo[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState("extract_glossary.md");
  const [promptFileContent, setPromptFileContent] = useState("");
  const [rendered, setRendered] = useState<PromptRenderResponse | null>(null);
  const [resultText, setResultText] = useState("");
  const [validation, setValidation] = useState<PromptValidationResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedProject) {
      return;
    }
    apiClient
      .listPrompts(selectedProject.project_ID)
      .then((response) => {
        setPrompts(response.prompts);
        if (response.prompts.length > 0 && !selectedPrompt) {
          setSelectedPrompt(response.prompts[0].name);
        }
      })
      .catch((err) => setError(errorText(err)));
  }, [selectedProject?.project_ID]);

  useEffect(() => {
    if (!selectedProject || !selectedPrompt) {
      return;
    }
    apiClient
      .getPrompt(selectedProject.project_ID, selectedPrompt)
      .then((response) => setPromptFileContent(response.content))
      .catch((err) => setError(errorText(err)));
  }, [selectedProject?.project_ID, selectedPrompt]);

  function requestBody() {
    return {
      task,
      scope: {
        volume: Number(scope.volume || 1),
        chapter: scope.chapter || null,
        segment_ID: scope.segment_ID || null,
        item_ID: scope.item_ID || null,
        sub_item_ID: scope.sub_item_ID || null
      }
    };
  }

  async function savePromptFile() {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.updatePrompt(selectedProject.project_ID, selectedPrompt, promptFileContent);
      setPromptFileContent(response.content);
      setMessage("Prompt file saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function generatePrompt() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.renderPrompt(selectedProject.project_ID, requestBody());
      setRendered(response);
      setMessage(`Rendered for ${response.provider_slot}.`);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function copyPrompt() {
    if (rendered?.prompt) {
      await navigator.clipboard.writeText(rendered.prompt);
      setMessage("Prompt copied.");
    }
  }

  async function runViaApi() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.runLLM(selectedProject.project_ID, requestBody());
      setRendered(response.render);
      setResultText(response.result_text);
      setMessage(`API job ${response.job.job_ID} completed.`);
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function validateResult() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.validatePromptResult(selectedProject.project_ID, {
        ...requestBody(),
        result_text: resultText
      });
      setValidation(response);
      setMessage(response.ok ? "Result is valid." : "Validation failed.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveResult() {
    if (!selectedProject) {
      setError("Select a project first.");
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.savePromptResult(selectedProject.project_ID, {
        ...requestBody(),
        result_text: resultText
      });
      setValidation(response.validation);
      setMessage(response.validation.ok ? `Saved ${response.records} records.` : "Validation failed; not saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Prompt Studio</span>
        <h1>Manual and API prompts</h1>
        <p>Render project prompt files, copy them to chat, run via API, validate pasted JSON, and save results.</p>
      </div>
      {!selectedProject && <div className="notice error">Select a project first.</div>}
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}
      <div className="prompt-layout">
        <div className="panel">
          <h2>Prompt file</h2>
          <label>
            File
            <select value={selectedPrompt} onChange={(event) => setSelectedPrompt(event.target.value)}>
              {prompts.map((prompt) => (
                <option key={prompt.name} value={prompt.name}>
                  {prompt.name}
                </option>
              ))}
            </select>
          </label>
          <textarea
            className="code-editor"
            value={promptFileContent}
            onChange={(event) => setPromptFileContent(event.target.value)}
          />
          <button type="button" onClick={savePromptFile} disabled={!selectedProject}>
            <Save size={18} />
            <span>Save Prompt File</span>
          </button>
        </div>
        <div className="panel">
          <h2>Render scope</h2>
          <label>
            Task
            <select
              value={task}
              onChange={(event) => {
                const nextTask = event.target.value as PromptTask;
                setTask(nextTask);
                setSelectedPrompt(`${nextTask}.md`);
              }}
            >
              {Object.entries(promptTaskLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div className="form-grid">
            <label>
              Volume
              <input
                type="number"
                min="1"
                value={scope.volume}
                onChange={(event) => setScope({ ...scope, volume: Number(event.target.value) })}
              />
            </label>
            <label>
              Chapter
              <input value={scope.chapter ?? ""} onChange={(event) => setScope({ ...scope, chapter: event.target.value })} />
            </label>
            <label>
              Segment ID
              <input
                value={scope.segment_ID ?? ""}
                onChange={(event) => setScope({ ...scope, segment_ID: event.target.value })}
              />
            </label>
            <label>
              Item ID
              <input value={scope.item_ID ?? ""} onChange={(event) => setScope({ ...scope, item_ID: event.target.value })} />
            </label>
            <label>
              Sub-item ID
              <input
                value={scope.sub_item_ID ?? ""}
                onChange={(event) => setScope({ ...scope, sub_item_ID: event.target.value })}
              />
            </label>
          </div>
          <div className="toolbar compact">
            <button type="button" onClick={generatePrompt} disabled={!selectedProject}>
              Generate Prompt
            </button>
            <button type="button" onClick={copyPrompt} disabled={!rendered}>
              <Clipboard size={18} />
              <span>Copy Prompt</span>
            </button>
            <button type="button" onClick={runViaApi} disabled={!selectedProject}>
              <Play size={18} />
              <span>Run via API</span>
            </button>
          </div>
          <textarea className="code-editor" readOnly value={rendered?.prompt ?? ""} />
          {rendered && (
            <div className="notice success">
              Expected schema: {rendered.expected_schema}; provider: {rendered.provider_slot}
            </div>
          )}
        </div>
        <div className="panel wide">
          <h2>Result editor</h2>
          <textarea
            className="code-editor result-editor"
            value={resultText}
            onChange={(event) => setResultText(event.target.value)}
          />
          <div className="toolbar compact">
            <button type="button" onClick={validateResult} disabled={!selectedProject || !resultText.trim()}>
              <CheckCircle2 size={18} />
              <span>Validate</span>
            </button>
            <button type="button" onClick={saveResult} disabled={!selectedProject || !resultText.trim()}>
              <Save size={18} />
              <span>Save</span>
            </button>
            <button type="button" onClick={() => setResultText("")}>
              <Trash2 size={18} />
              <span>Clear</span>
            </button>
          </div>
          {validation && (
            <div className={validation.ok ? "notice success" : "notice error"}>
              {validation.ok ? "Result JSON matches expected schema." : validation.errors.join(" ")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

