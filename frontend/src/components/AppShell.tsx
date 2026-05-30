import { BookOpen, FolderKanban } from "lucide-react";

import { navItems } from "../appData";
import type { AppShellProps } from "../types";

export function AppShell({ active, setActive, health, selectedProject, children }: AppShellProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="topbar">
          <div className="brand">
            <BookOpen size={24} />
            <div>
              <strong>Novel Studio</strong>
              <span>Translation workspace</span>
            </div>
          </div>
          <div className="project-bar">
            <FolderKanban size={18} />
            <div>
              <span className="eyebrow">Current project</span>
              <strong>{selectedProject ? selectedProject.name : "No project selected"}</strong>
              {selectedProject && <span className="topbar-path">{selectedProject.root}</span>}
            </div>
          </div>
          <div className={health?.status === "ok" ? "health ok" : "health"}>
            <span className="health-dot" />
            <span>{health ? `API ${health.status} - v${health.app_version}` : "API offline"}</span>
          </div>
        </div>
        <nav className="top-nav" aria-label="Primary">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={active === item.key ? "nav-item active" : "nav-item"}
                key={item.key}
                onClick={() => setActive(item.key)}
                type="button"
                title={item.label}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </header>
      <div className="workspace">
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
