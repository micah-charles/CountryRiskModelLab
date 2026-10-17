import { getCurrentVersion, getSnapshotBody, getVersion, isSnapshotDataset, toVersionManifest } from "@/lib/snapshots";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ datasetKey: string }> }) {
  const { datasetKey } = await context.params;
  if (!isSnapshotDataset(datasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  const requestedVersion = new URL(request.url).searchParams.get("version");
  try {
    const row = requestedVersion ? await getVersion(datasetKey, Number(requestedVersion)) : await getCurrentVersion(datasetKey);
    if (!row) return Response.json({ error: "No snapshot has been published yet.", datasetKey, version: null }, { status: 404 });
    const manifest = toVersionManifest(row);
    const snapshot = await getSnapshotBody(row.object_key);
    const payload = datasetKey === "bond-yields" && !isLocalBondDataAccessEnabled()
      ? { datasetKey, version: row.version, manifest, snapshot: summarizeBondSnapshot(snapshot) }
      : { datasetKey, version: row.version, manifest, snapshot };
    return Response.json(payload, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Snapshot could not be read." }, { status: 503 });
  }
}

function summarizeBondSnapshot(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Bond snapshot has an invalid shape.");
  const snapshot = value as Record<string, unknown>;
  const series = snapshot.series && typeof snapshot.series === "object" && !Array.isArray(snapshot.series)
    ? snapshot.series as Record<string, unknown> : {};
  const summary: Record<string, { observationCount: number; firstObservation: string; latestObservation: string; latestValue: number | null }> = {};
  for (const [country, valueRows] of Object.entries(series)) {
    if (!Array.isArray(valueRows) || !valueRows.length) continue;
    const rows = valueRows.filter((row): row is { date: string; value: number | null } => {
      if (!row || typeof row !== "object") return false;
      const point = row as { date?: unknown; value?: unknown };
      return typeof point.date === "string" && (point.value === null || typeof point.value === "number");
    });
    if (!rows.length) continue;
    const latest = [...rows].reverse().find((row) => typeof row.value === "number" && Number.isFinite(row.value));
    summary[country] = { observationCount: rows.length, firstObservation: rows[0].date, latestObservation: rows.at(-1)!.date, latestValue: latest?.value ?? null };
  }
  return {
    datasetKey: snapshot.datasetKey,
    periodStart: snapshot.periodStart,
    retrievedAt: snapshot.retrievedAt,
    historyComplete: snapshot.historyComplete,
    missingValuePolicy: snapshot.missingValuePolicy,
    operatorSelectedPurpose: snapshot.operatorSelectedPurpose,
    sourceRightsStatus: snapshot.sourceRightsStatus,
    restrictedCountries: Array.isArray(snapshot.restrictedCountries) ? snapshot.restrictedCountries : [],
    note: snapshot.note,
    sources: snapshot.sources,
    sourceStatus: snapshot.sourceStatus,
    seriesSummary: summary,
  };
}
