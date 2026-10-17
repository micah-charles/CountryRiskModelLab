"use client";

import { useEffect, useState } from "react";

export type SnapshotEnvelope<T = unknown> = { datasetKey: string; version: number; manifest: Record<string, unknown>; snapshot: T };
export type LoadState<T = unknown> = { status: "loading" | "ready" | "empty" | "error"; value?: SnapshotEnvelope<T>; message?: string };

export function useSnapshot<T = unknown>(datasetKey: string): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({ status: "loading" });
  useEffect(() => {
    let active = true;
    fetch(`/api/snapshots/${encodeURIComponent(datasetKey)}`, { cache: "no-store" })
      .then(async (response) => {
        const body = await response.json().catch(() => ({})) as Record<string, unknown>;
        if (!response.ok) {
          const message = typeof body.error === "string" ? body.error : "Snapshot is unavailable.";
          if (response.status === 404) return { status: "empty" as const, message };
          throw new Error(message);
        }
        return { status: "ready" as const, value: body as SnapshotEnvelope<T> };
      })
      .then((next) => { if (active) setState(next); })
      .catch((error: unknown) => { if (active) setState({ status: "error", message: error instanceof Error ? error.message : "Snapshot is unavailable." }); });
    return () => { active = false; };
  }, [datasetKey]);
  return state;
}
