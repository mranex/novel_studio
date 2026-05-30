import {
  Brush,
  Database,
  FileDown,
  FolderKanban,
  GitBranch,
  MessageCircle,
  MessageSquareText,
  Settings,
  Upload,
  Workflow
} from "lucide-react";

import type { PromptTask } from "./api/client";
import type { NavItem, PageKey } from "./types";

export const promptTaskLabels: Record<PromptTask, string> = {
  segment_source: "Segment Source",
  extract_glossary: "Extract Glossary",
  extract_relationship: "Extract Relationship",
  label_dialogue: "Label Dialogue",
  translate: "Translate"
};

export const navItems: NavItem[] = [
  { key: "project-manager", label: "Project Manager", icon: FolderKanban },
  { key: "import-source", label: "Import Source", icon: Upload },
  { key: "workflow", label: "Workflow", icon: Workflow },
  { key: "prompt-studio", label: "Prompt Studio", icon: MessageSquareText },
  { key: "database-editor", label: "Database Editor", icon: Database },
  { key: "relationship-canvas", label: "Relationship Canvas", icon: GitBranch },
  { key: "dialogue-labels", label: "Dialogue Labels", icon: MessageCircle },
  { key: "polish-center", label: "Polish Center", icon: Brush },
  { key: "export", label: "Export", icon: FileDown },
  { key: "config", label: "Config", icon: Settings }
];

export const placeholders: Record<PageKey, string> = {
  "project-manager": "Create and open local project folders.",
  "import-source": "Import source and segment JSON files.",
  workflow: "Track each volume through the translation pipeline.",
  "prompt-studio": "Generate prompts, paste results, validate, and save.",
  "database-editor": "Review and edit glossary pipeline tables.",
  "relationship-canvas": "Review character relationships on a timeline.",
  "dialogue-labels": "Review dialogue speaker and listener labels.",
  "polish-center": "Regenerate, polish, and preview translated text.",
  export: "Export selected volumes to readable output formats.",
  config: "Manage local provider and project settings."
};

export const statusLabels: Record<string, string> = {
  not_started: "Not started",
  ready: "Ready",
  ready_for_skeleton: "Ready for skeleton",
  running: "Running",
  needs_review: "Needs review",
  completed: "Completed",
  failed: "Failed"
};
