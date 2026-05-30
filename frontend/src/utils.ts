import type { ProjectMetadata } from "./api/client";
import type { ImportFileState, ProjectLike, SelectedProject } from "./types";

export function classForStatus(status: string): string {
  return `status status-${status.replace(/_/g, "-")}`;
}

export function makeSelectedProject(project: ProjectLike): SelectedProject {
  if ("metadata" in project) {
    return {
      project_ID: project.metadata.project_ID,
      root: project.root,
      name: project.metadata.name
    };
  }
  return {
    project_ID: project.project_ID,
    root: project.root,
    name: project.name
  };
}

export function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Unexpected error.";
}

export async function readImportFile(file: File): Promise<ImportFileState> {
  return { filename: file.name, text: await file.text() };
}

export type MetadataField = keyof ProjectMetadata;

