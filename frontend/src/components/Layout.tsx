import type { ReactNode } from "react";
import { Sidebar, type PageKey } from "./Sidebar";

export function Layout({ active, onNavigate, children }: { active: PageKey; onNavigate: (page: PageKey) => void; children: ReactNode }) {
  return (
    <div className="app-shell">
      <Sidebar active={active} onNavigate={onNavigate} />
      <main className="workspace">{children}</main>
    </div>
  );
}

