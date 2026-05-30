import { FolderOpen, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { apiClient, ProjectDetail, ProjectListItem, ProjectMetadata } from "../api/client";
import type { SelectedProject } from "../types";
import { errorText, makeSelectedProject } from "../utils";

export function ProjectManager({
  selectedProject,
  onSelect
}: {
  selectedProject: SelectedProject | null;
  onSelect: (project: SelectedProject) => void;
}) {
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({
    root: "",
    name: "",
    genre: "xianxia",
    source_language: "zh",
    target_language: "vi",
    notes: ""
  });
  const [openRoot, setOpenRoot] = useState("");

  async function refreshProjects() {
    const response = await apiClient.listProjects();
    setProjects(response.projects);
  }

  async function loadProject(projectId: string) {
    const response = await apiClient.getProject(projectId);
    setDetail(response);
    onSelect(makeSelectedProject(response));
  }

  useEffect(() => {
    refreshProjects().catch((err) => setError(errorText(err)));
  }, []);

  useEffect(() => {
    if (selectedProject) {
      loadProject(selectedProject.project_ID).catch((err) => setError(errorText(err)));
    }
  }, [selectedProject?.project_ID]);

  async function createProject() {
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.createProject(createForm);
      const project = {
        project_ID: response.metadata.project_ID,
        root: response.root,
        name: response.metadata.name
      };
      onSelect(project);
      await refreshProjects();
      await loadProject(project.project_ID);
      setMessage("Project created.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function openProject() {
    setError(null);
    setMessage(null);
    try {
      const response = await apiClient.openProject(openRoot);
      const project = {
        project_ID: response.metadata.project_ID,
        root: response.root,
        name: response.metadata.name
      };
      onSelect(project);
      await refreshProjects();
      await loadProject(project.project_ID);
      setMessage("Project opened.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  async function saveMetadata() {
    if (!detail) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      const updated = await apiClient.updateMetadata(detail.metadata.project_ID, {
        name: detail.metadata.name,
        genre: detail.metadata.genre,
        source_language: detail.metadata.source_language,
        target_language: detail.metadata.target_language,
        notes: detail.metadata.notes
      });
      setDetail(updated);
      onSelect(makeSelectedProject(updated));
      await refreshProjects();
      setMessage("Metadata saved.");
    } catch (err) {
      setError(errorText(err));
    }
  }

  function updateMetadataField<K extends keyof ProjectMetadata>(key: K, value: ProjectMetadata[K]) {
    if (!detail) {
      return;
    }
    setDetail({ ...detail, metadata: { ...detail.metadata, [key]: value } });
  }

  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Project Manager</span>
        <h1>Projects</h1>
        <p>Create, open, and inspect local Novel Studio project folders.</p>
      </div>

      {error && <div className="notice error">{error}</div>}
      {message && <div className="notice success">{message}</div>}

      <div className="manager-layout">
        <div className="panel">
          <h2>Create project</h2>
          <label>
            Folder path
            <input value={createForm.root} onChange={(event) => setCreateForm({ ...createForm, root: event.target.value })} />
          </label>
          <label>
            Novel name
            <input value={createForm.name} onChange={(event) => setCreateForm({ ...createForm, name: event.target.value })} />
          </label>
          <div className="form-grid">
            <label>
              Genre
              <input
                value={createForm.genre}
                onChange={(event) => setCreateForm({ ...createForm, genre: event.target.value })}
              />
            </label>
            <label>
              Source
              <input
                value={createForm.source_language}
                onChange={(event) => setCreateForm({ ...createForm, source_language: event.target.value })}
              />
            </label>
            <label>
              Target
              <input
                value={createForm.target_language}
                onChange={(event) => setCreateForm({ ...createForm, target_language: event.target.value })}
              />
            </label>
          </div>
          <label>
            Notes
            <textarea
              value={createForm.notes}
              onChange={(event) => setCreateForm({ ...createForm, notes: event.target.value })}
            />
          </label>
          <button type="button" onClick={createProject}>
            <Save size={18} />
            <span>Create Project</span>
          </button>
        </div>

        <div className="panel">
          <h2>Open folder</h2>
          <div className="inline-form">
            <input value={openRoot} onChange={(event) => setOpenRoot(event.target.value)} placeholder="C:\\Novels\\Project" />
            <button type="button" onClick={openProject}>
              <FolderOpen size={18} />
              <span>Open</span>
            </button>
          </div>
          <h2>Known projects</h2>
          <div className="project-list">
            {projects.map((project) => (
              <button
                className={selectedProject?.project_ID === project.project_ID ? "project-card active" : "project-card"}
                key={project.project_ID}
                onClick={() => loadProject(project.project_ID)}
                type="button"
              >
                <strong>{project.name}</strong>
                <span>{project.root}</span>
              </button>
            ))}
            {projects.length === 0 && <span className="muted">No registered projects yet.</span>}
          </div>
        </div>

        <div className="panel wide">
          <h2>Metadata and health</h2>
          {detail ? (
            <>
              <div className="form-grid">
                <label>
                  Novel name
                  <input
                    value={detail.metadata.name}
                    onChange={(event) => updateMetadataField("name", event.target.value)}
                  />
                </label>
                <label>
                  Genre
                  <input
                    value={detail.metadata.genre}
                    onChange={(event) => updateMetadataField("genre", event.target.value)}
                  />
                </label>
                <label>
                  Source
                  <input
                    value={detail.metadata.source_language}
                    onChange={(event) => updateMetadataField("source_language", event.target.value)}
                  />
                </label>
                <label>
                  Target
                  <input
                    value={detail.metadata.target_language}
                    onChange={(event) => updateMetadataField("target_language", event.target.value)}
                  />
                </label>
              </div>
              <label>
                Notes
                <textarea
                  value={detail.metadata.notes}
                  onChange={(event) => updateMetadataField("notes", event.target.value)}
                />
              </label>
              <button type="button" onClick={saveMetadata}>
                <Save size={18} />
                <span>Save Metadata</span>
              </button>
              <div className="metric-grid">
                <div>
                  <strong>{detail.health.volumes_imported}</strong>
                  <span>Volumes</span>
                </div>
                <div>
                  <strong>{detail.health.chapters_imported}</strong>
                  <span>Chapters</span>
                </div>
                <div>
                  <strong>{detail.health.segments_imported}</strong>
                  <span>Segments</span>
                </div>
              </div>
            </>
          ) : (
            <span className="muted">Select or create a project.</span>
          )}
        </div>
      </div>
    </section>
  );
}
