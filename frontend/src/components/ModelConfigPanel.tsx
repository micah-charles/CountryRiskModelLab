import type { ReactNode } from "react";

export function ModelConfigPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="config-panel">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

