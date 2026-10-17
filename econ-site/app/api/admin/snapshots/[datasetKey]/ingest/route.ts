import { assertNoHistoryLoss, collectChanges, getCurrentVersion, getDatabase, getHostedBondCountries, getRawFileLimit, getSnapshotBody, isSnapshotDataset, sha256, validateSnapshot } from "@/lib/snapshots";
import type { SnapshotDataset } from "@/lib/snapshots";
import { getBucket } from "@/lib/snapshots";
import { renderBondChartAssets } from "@/lib/bond-chart-assets";
import type { BondSnapshot } from "@/app/data/catalog";

export const dynamic = "force-dynamic";

type RawInput = { name: string; sha256: string; contentBase64: string };
type IngestBody = { expectedVersion: number | null; snapshot: unknown; rawSnapshots?: RawInput[]; sourceStatus?: unknown };

export async function POST(request: Request, context: { params: Promise<{ datasetKey: string }> }) {
  const { datasetKey: rawDatasetKey } = await context.params;
  if (!isSnapshotDataset(rawDatasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  const datasetKey = rawDatasetKey as SnapshotDataset;
  if (request.headers.has("origin")) {
    try {
      if (new URL(request.headers.get("origin")!).origin !== new URL(request.url).origin) {
        return Response.json({ error: "Cross-site snapshot writes are not allowed." }, { status: 403 });
      }
    } catch {
      return Response.json({ error: "Invalid request origin." }, { status: 403 });
    }
  }

  let body: IngestBody;
  try {
    body = await request.json() as IngestBody;
    if (!Number.isInteger(body.expectedVersion) && body.expectedVersion !== null) throw new Error("expectedVersion must be an integer or null");
    if (body.expectedVersion !== null && body.expectedVersion < 1) throw new Error("expectedVersion must be positive");
    validateSnapshot(datasetKey, body.snapshot);
    if (!Array.isArray(body.rawSnapshots ?? [])) throw new Error("rawSnapshots must be an array");
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Invalid snapshot payload." }, { status: 400 });
  }

  try {
    const current = await getCurrentVersion(datasetKey);
    const actualVersion = current?.version ?? null;
    if (actualVersion !== body.expectedVersion) {
      return Response.json({ error: "Snapshot head changed during this update.", expectedVersion: body.expectedVersion, actualVersion }, { status: 409 });
    }
    const previousSnapshot = current ? await getSnapshotBody(current.object_key) : null;
    if (!current && Object.values((body.snapshot as Record<string, unknown>).sourceStatus as Record<string, { status?: string }>).some((status) => status?.status === "stale")) {
      return Response.json({ error: "A first snapshot cannot publish stale source data without an existing last-good version." }, { status: 409 });
    }
    if (previousSnapshot) assertNoHistoryLoss(datasetKey, previousSnapshot, body.snapshot);
    const changeSet = collectChanges(datasetKey, previousSnapshot, body.snapshot);
    const version = (actualVersion ?? 0) + 1;
    const now = new Date().toISOString();
    const snapshotText = JSON.stringify(body.snapshot);
    const snapshotHash = await sha256(snapshotText);
    const baseKey = `snapshots/${datasetKey}/v${version}`;
    const objectKey = `${baseKey}/${snapshotHash}.json`;
    const diffText = JSON.stringify({ datasetKey, version, createdAt: now, changes: changeSet.all });
    const diffHash = await sha256(diffText);
    const diffObjectKey = `${baseKey}/diff-${diffHash}.json`;
    const rawSnapshots: Array<{ name: string; sha256: string; objectKey: string }> = [];
    const chartAssets: Array<{ period: string; country: string; sha256: string; objectKey: string }> = [];

    await getBucket().put(objectKey, snapshotText, { httpMetadata: { contentType: "application/json; charset=utf-8" } });
    await getBucket().put(diffObjectKey, diffText, { httpMetadata: { contentType: "application/json; charset=utf-8" } });
    if (datasetKey === "bond-yields") {
      const artifacts = renderBondChartAssets(body.snapshot as BondSnapshot, version, snapshotHash);
      for (const artifact of artifacts) {
        const digest = await sha256(artifact.svg);
        await getBucket().put(artifact.objectKey, artifact.svg, { httpMetadata: { contentType: "image/svg+xml; charset=utf-8", cacheControl: "private, max-age=31536000, immutable" } });
        chartAssets.push({ period: artifact.period, country: artifact.country, sha256: digest, objectKey: artifact.objectKey });
      }
    }
    for (const raw of body.rawSnapshots ?? []) {
      const prefixes: Record<string, string> = { US: "us", UK: "uk", France: "fr", Italy: "it", Germany: "germany", Japan: "japan" };
      const allowedPrefix = getHostedBondCountries().map((country) => prefixes[country]).filter(Boolean);
      const allowedName = new RegExp(`^(?:${allowedPrefix.join("|")})[a-z0-9._-]*\\.(?:csv|zip)$`, "i");
      if (datasetKey !== "bond-yields" || !allowedName.test(raw.name)) {
        throw new Error("Raw source files are accepted only for countries enabled by the server-side presentation-purpose configuration.");
      }
      if (!/^[0-9a-f]{64}$/i.test(raw.sha256) || !/^[A-Za-z0-9+/]*={0,2}$/.test(raw.contentBase64)) {
        throw new Error(`Invalid raw snapshot encoding for ${raw.name}`);
      }
      const bytes = Uint8Array.from(atob(raw.contentBase64), (character) => character.charCodeAt(0));
      if (bytes.byteLength > getRawFileLimit()) throw new Error(`Raw snapshot ${raw.name} exceeds the upload limit.`);
      if (await sha256(bytes.buffer) !== raw.sha256.toLowerCase()) throw new Error(`SHA-256 mismatch for ${raw.name}`);
      const rawObjectKey = `${baseKey}/raw/${raw.sha256.toLowerCase()}-${raw.name}`;
      await getBucket().put(rawObjectKey, bytes, { httpMetadata: { contentType: raw.name.endsWith(".zip") ? "application/zip" : "text/csv" } });
      rawSnapshots.push({ name: raw.name, sha256: raw.sha256.toLowerCase(), objectKey: rawObjectKey });
    }

    const sourceCounts = datasetKey === "bond-yields"
      ? Object.fromEntries(Object.entries((body.snapshot as Record<string, unknown>).series as Record<string, unknown>).map(([country, rows]) => [country, Array.isArray(rows) ? rows.length : 0]))
      : {};
    const manifest = {
      changeCount: changeSet.all.length,
      recentChangeCount: changeSet.recentCount,
      diffObjectKey,
      rawSnapshots,
      chartAssets,
      sourceStatus: body.sourceStatus ?? (body.snapshot as Record<string, unknown>).sourceStatus ?? {},
      summary: { sourceCounts, latestPublishedAt: (body.snapshot as Record<string, unknown>).retrievedAt ?? now },
    };
    const db = getDatabase();
    const statements = [
      db.prepare(
        `INSERT INTO snapshot_versions (dataset_key, version, object_key, snapshot_sha256, manifest_json, previous_version, restored_from_version, created_at, created_by)
         VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 'scheduled-updater')`,
      ).bind(datasetKey, version, objectKey, snapshotHash, JSON.stringify(manifest), actualVersion, now),
      db.prepare(
        `INSERT INTO snapshot_diffs (dataset_key, version, diff_object_key, change_count, recent_change_count, observed_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      ).bind(datasetKey, version, diffObjectKey, changeSet.all.length, changeSet.recentCount, now),
      db.prepare(
        `INSERT INTO snapshot_heads (dataset_key, version, updated_at) VALUES (?, ?, ?)
         ON CONFLICT(dataset_key) DO UPDATE SET version = excluded.version, updated_at = excluded.updated_at`,
      ).bind(datasetKey, version, now),
    ];
    try {
      await db.batch(statements);
    } catch (error) {
      // Reusing a version number is prevented by the immutable version primary key.
      // A concurrent writer can leave unreachable R2 objects, but never moves the head.
      const latest = await getCurrentVersion(datasetKey).catch(() => null);
      const latestVersion = latest?.version ?? null;
      if (latestVersion !== actualVersion) {
        return Response.json({ error: "Snapshot head changed during this update.", expectedVersion: actualVersion, actualVersion: latestVersion }, { status: 409 });
      }
      throw new Error(`Snapshot transaction failed; current version was preserved. ${error instanceof Error ? error.message : ""}`);
    }
    return Response.json({ datasetKey, version, snapshotSha256: snapshotHash, previousVersion: actualVersion, changeCount: changeSet.all.length, recentChangeCount: changeSet.recentCount, rawSnapshots }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Snapshot could not be stored." }, { status: 503 });
  }
}
