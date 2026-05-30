import { PlugZap, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { apiClient, AppSettings, ProjectSettings } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText } from "../utils";

export function ConfigPage({ selectedProject }: { selectedProject: SelectedProject | null }) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [projectSettings, setProjectSettings] = useState<ProjectSettings | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiClient
      .getSettings()
      .then((response) => setSettings(response.app))
      .catch((err) => setError(errorText(err)));
  }, []);

  useEffect(() => {
    if (!selectedProject) {
      setProjectSettings(null);
      return;
    }
    apiClient.getProject(selectedProject.project_ID).then((response) => setProjectSettings(response.settings)).catch(() => undefined);
  }, [selectedProject?.project_ID]);

  function updateProvider(slot: "small_llm" | "big_llm", field: keyof AppSettings["small_llm"], value: string) {
    if (!settings) {
      return;
    }
    setSettings({ ...settings, [slot]: { ...settings[slot], [field]: value } });
  }

  async function saveSettings() {
    if (!settings) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.updateSettings(settings);
      setSettings(response);
      setMessage("Settings saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveProjectSettings() {
    if (!selectedProject || !projectSettings) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.updateProjectSettings(selectedProject.project_ID, projectSettings);
      setProjectSettings(response);
      setMessage("Project settings saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function testProvider(slot: "small_llm" | "big_llm") {
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.testProvider(slot);
      if (response.ok) {
        setMessage(`${slot === "small_llm" ? "Small" : "Big"} provider connection succeeded.`);
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Config</span>
        <h1>Provider settings</h1>
        <p>Configure OpenAI-compatible provider slots used by Prompt Studio.</p>
      </div>
      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}
      {settings && (
        <div className="manager-layout">
          {(["small_llm", "big_llm"] as const).map((slot) => (
            <div className="panel" key={slot}>
              <h2>{slot === "small_llm" ? "Small LLM" : "Big LLM"}</h2>
              <label>
                Base URL
                <input value={settings[slot].base_url} onChange={(event) => updateProvider(slot, "base_url", event.target.value)} />
              </label>
              <label>
                API key
                <input
                  type="password"
                  value={settings[slot].api_key}
                  onChange={(event) => updateProvider(slot, "api_key", event.target.value)}
                  placeholder="Empty is allowed for local providers"
                />
              </label>
              <label>
                Model
                <input value={settings[slot].model} onChange={(event) => updateProvider(slot, "model", event.target.value)} />
              </label>
              <button type="button" onClick={() => testProvider(slot)}>
                <PlugZap size={18} />
                <span>Test Connection</span>
              </button>
            </div>
          ))}
          <div className="panel wide">
            <label>
              Batch count
              <input
                type="number"
                min="1"
                value={settings.batch_count}
                onChange={(event) => setSettings({ ...settings, batch_count: Number(event.target.value) })}
              />
            </label>
            <button type="button" onClick={saveSettings}>
              <Save size={18} />
              <span>Save App Settings</span>
            </button>
          </div>
          <div className="panel wide">
            <h2>Project processing</h2>
            {!projectSettings && <span className="muted">Select a project to edit project-level settings.</span>}
            {projectSettings && (
              <>
                <div className="form-grid">
                  <label>
                    Max sub-item tokens
                    <input
                      type="number"
                      min="1"
                      value={projectSettings.max_subitem_tokens}
                      onChange={(event) =>
                        setProjectSettings({ ...projectSettings, max_subitem_tokens: Number(event.target.value || 1) })
                      }
                    />
                  </label>
                  <label>
                    Prompt folder
                    <input
                      value={projectSettings.prompt_folder}
                      onChange={(event) => setProjectSettings({ ...projectSettings, prompt_folder: event.target.value })}
                    />
                  </label>
                  <label>
                    Batch override
                    <input
                      type="number"
                      min="1"
                      value={projectSettings.batch_count_override ?? ""}
                      onChange={(event) =>
                        setProjectSettings({
                          ...projectSettings,
                          batch_count_override: event.target.value ? Number(event.target.value) : null
                        })
                      }
                    />
                  </label>
                </div>
                <div className="notice">
                  API keys are stored only in app settings. Project folders are shareable, so provider secrets should not be saved
                  there.
                </div>
                <button type="button" onClick={saveProjectSettings}>
                  <Save size={18} />
                  <span>Save Project Settings</span>
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
