import { useEffect, useMemo, useState } from "react";

import { apiClient, HealthResponse } from "./api/client";
import { AppShell } from "./components/AppShell";
import { ConfigPage } from "./pages/ConfigPage";
import { DatabaseEditor } from "./pages/DatabaseEditor";
import { DialogueLabels } from "./pages/DialogueLabels";
import { ExportPage } from "./pages/ExportPage";
import { GlossaryReview } from "./pages/GlossaryReview";
import { ImportSource } from "./pages/ImportSource";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { ProjectManager } from "./pages/ProjectManager";
import { PromptStudio } from "./pages/PromptStudio";
import { PolishCenter } from "./pages/PolishCenter";
import { RelationshipCanvas } from "./pages/RelationshipCanvas";
import { WorkflowDashboard } from "./pages/WorkflowDashboard";
import type { PageKey, SelectedProject } from "./types";

export function App() {
  const [active, setActive] = useState<PageKey>("project-manager");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedProject, setSelectedProject] = useState<SelectedProject | null>(null);

  useEffect(() => {
    apiClient.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  const page = useMemo(() => {
    if (active === "project-manager") {
      return <ProjectManager selectedProject={selectedProject} onSelect={setSelectedProject} />;
    }
    if (active === "import-source") {
      return <ImportSource selectedProject={selectedProject} />;
    }
    if (active === "workflow") {
      return <WorkflowDashboard selectedProject={selectedProject} />;
    }
    if (active === "prompt-studio") {
      return <PromptStudio selectedProject={selectedProject} />;
    }
    if (active === "database-editor") {
      return <DatabaseEditor selectedProject={selectedProject} />;
    }
    if (active === "relationship-canvas") {
      return <RelationshipCanvas selectedProject={selectedProject} />;
    }
    if (active === "dialogue-labels") {
      return <DialogueLabels selectedProject={selectedProject} />;
    }
    if (active === "polish-center") {
      return <PolishCenter selectedProject={selectedProject} />;
    }
    if (active === "export") {
      return <ExportPage selectedProject={selectedProject} />;
    }
    if (active === "config") {
      return <ConfigPage selectedProject={selectedProject} />;
    }
    return <PlaceholderPage page={active} />;
  }, [active, selectedProject]);

  return (
    <AppShell active={active} setActive={setActive} health={health} selectedProject={selectedProject}>
      {page}
    </AppShell>
  );
}
