import type { ComponentType, ReactNode } from "react";

import type { HealthResponse, ProjectDetail, ProjectListItem } from "./api/client";

export type PageKey =
  | "project-manager"
  | "import-source"
  | "workflow"
  | "prompt-studio"
  | "database-editor"
  | "relationship-canvas"
  | "dialogue-labels"
  | "polish-center"
  | "export"
  | "config";

export type NavItem = {
  key: PageKey;
  label: string;
  icon: ComponentType<{ size?: number }>;
};

export type SelectedProject = {
  project_ID: string;
  root: string;
  name: string;
};

export type ImportFileState = {
  filename: string;
  text: string;
};

export type AppShellProps = {
  active: PageKey;
  setActive: (page: PageKey) => void;
  health: HealthResponse | null;
  selectedProject: SelectedProject | null;
  children: ReactNode;
};

export type ProjectLike = ProjectDetail | ProjectListItem;
