import { POST as ingest } from "@/app/api/admin/snapshots/[datasetKey]/ingest/route";
import { getCurrentVersion, getSnapshotBody, getHostedBondCountries, getBondPresentationPurpose, sha256 } from "@/lib/snapshots";
import { base64, fetchCountry, OFFICIAL_SOURCES } from "@/lib/official-bond-refresh";
import type { Observation, OfficialCountry } from "@/lib/official-bond-refresh";

export const dynamic = "force-dynamic";

/** Owner-private dispatch boundary also authorizes unattended Site service calls.
 * Source downloads occur here; no GitHub data copy or online Mac is required.
 */
export async function POST(request: Request) {
  const origin = request.headers.get("origin");
  if (origin && origin !== new URL(request.url).origin) return Response.json({ error: "Cross-site refresh is forbidden" }, { status: 403 });
  try {
    const current = await getCurrentVersion("bond-yields");
    const previous = current ? await getSnapshotBody(current.object_key) as {
      series?: Record<string, Observation[]>;
      sources?: Record<string, unknown>;
      sourceStatus?: Record<string, Record<string, unknown>>;
    } : null;
    const now = new Date(), attemptedAt = now.toISOString();
    const countries = getHostedBondCountries() as OfficialCountry[];
    const series: Record<string, Observation[]> = {}, sources: Record<string, unknown> = {}, sourceStatus: Record<string, unknown> = {};
    const rawSnapshots: Array<{name: string; sha256: string; contentBase64: string}> = [];
    const results = await Promise.allSettled(countries.map((country) => fetchCountry(country, now)));
    const failures: string[] = [];
    for (let i = 0; i < countries.length; i++) {
      const country = countries[i], result = results[i];
      const before: Observation[] = previous?.series?.[country] ?? [];
      let failure = result.status === "rejected" ? String(result.reason?.message ?? result.reason) : "";
      if (result.status === "fulfilled" && before.length) {
        const dates = new Set(result.value.rows.map((row) => row.date));
        if (before.some((row) => !dates.has(row.date))) failure = "Full-history download lost previously published dates; last-good data retained for review";
      }
      if (failure) {
        failures.push(country);
        if (!before.length) return Response.json({ error: `Initial snapshot cannot be complete: ${country} unavailable`, details: failure }, { status: 503 });
        series[country] = before;
        sources[country] = previous?.sources?.[country] ?? { ...OFFICIAL_SOURCES[country], sourceUrl: OFFICIAL_SOURCES[country].source_url, seriesId: OFFICIAL_SOURCES[country].series_id };
        sourceStatus[country] = { ...(previous?.sourceStatus?.[country] ?? {}), status: "stale", lastAttemptAt: attemptedAt, error: failure, retainedFromVersion: current!.version, latestObservation: before.at(-1)?.date };
      } else if (result.status === "fulfilled") {
        const { rows, raw } = result.value;
        series[country] = rows;
        const rawFiles = [];
        for (const file of raw) {
          const digest = await sha256(file.bytes.buffer as ArrayBuffer);
          rawSnapshots.push({ name: file.name, sha256: digest, contentBase64: base64(file.bytes) });
          rawFiles.push({ name: file.name, sha256: digest, downloadUrl: file.url });
        }
        sources[country] = { ...OFFICIAL_SOURCES[country], sourceUrl: OFFICIAL_SOURCES[country].source_url, seriesId: OFFICIAL_SOURCES[country].series_id, first_observation: rows[0].date, latest_observation: rows.at(-1)!.date, latest_value_pct: rows.at(-1)!.value, observation_count: rows.length, rawFiles };
        sourceStatus[country] = { status: "current", lastAttemptAt: attemptedAt, lastSuccessAt: attemptedAt, latestObservation: rows.at(-1)!.date, observationCount: rows.length };
      }
    }
    const operatorSelectedPurpose = getBondPresentationPurpose();
    const restrictedCountries = ["France", "Italy"].filter((country) => !countries.includes(country as OfficialCountry));
    const rightsReview = operatorSelectedPurpose ? { France: "not-verified", Italy: "not-verified" } as const : undefined;
    const note = operatorSelectedPurpose
      ? "Operator-selected purpose: personal interview. This records intended use only; it is not a rights determination or verified permission. Euronext and Banca d'Italia terms apply; written permission has not been verified. Italy BMK0200 upstream vendors are not itemized. The interactive Site view loads prepared chart images and source summaries; owner-only CSV, JSON, and Excel downloads read the selected immutable stored snapshot."
      : "Country definitions differ; source gaps are never filled. France and Italy remain outside the configured Site snapshot until an explicit presentation purpose is selected.";
    const snapshot = { schemaVersion: 1, datasetKey: "bond-yields", periodStart: "2020-01-01", retrievedAt: attemptedAt, historyComplete: true, missingValuePolicy: "blank-no-fill", series, sources, sourceStatus, restrictedCountries, operatorSelectedPurpose, sourceRightsStatus: rightsReview, revisionWindow: "Previous two full calendar months plus current month; full-history downloads retained", note };
    const response = await ingest(new Request(new URL("/api/admin/snapshots/bond-yields/ingest", request.url), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expectedVersion: current?.version ?? null, snapshot, rawSnapshots, sourceStatus }) }), { params: Promise.resolve({ datasetKey: "bond-yields" }) });
    const result = await response.json() as Record<string, unknown>;
    return Response.json({ ...result, failures, refreshedAt: attemptedAt }, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Refresh failed; previous cloud snapshot preserved" }, { status: 503 });
  }
}
