import { collectChanges, getCurrentVersion, getDatabase, getSnapshotBody, getVersion, getVersionManifest, isSnapshotDataset, sha256, validateSnapshot } from "@/lib/snapshots";
import { getBucket } from "@/lib/snapshots";
import { renderBondChartAssets } from "@/lib/bond-chart-assets";
import type { BondSnapshot } from "@/app/data/catalog";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ datasetKey: string }> }) {
  const { datasetKey } = await context.params;
  if (!isSnapshotDataset(datasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  if (request.headers.has("origin")) {
    try {
      if (new URL(request.headers.get("origin")!).origin !== new URL(request.url).origin) {
        return Response.json({ error: "Cross-site snapshot restores are not allowed." }, { status: 403 });
      }
    } catch {
      return Response.json({ error: "Invalid request origin." }, { status: 403 });
    }
  }

  let restoredVersion: number;
  let expectedVersion: number | null;
  try {
    const body = await request.json() as { version?: number; expectedVersion?: number | null };
    restoredVersion = Number(body.version);
    expectedVersion = body.expectedVersion ?? null;
    if (!Number.isInteger(restoredVersion) || restoredVersion < 1) throw new Error("version must be a positive integer");
    if (expectedVersion !== null && (!Number.isInteger(expectedVersion) || expectedVersion < 1)) throw new Error("expectedVersion must be a positive integer or null");
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Invalid restore request." }, { status: 400 });
  }

  try {
    const current = await getCurrentVersion(datasetKey);
    const currentVersion = current?.version ?? null;
    if (currentVersion !== expectedVersion) return Response.json({ error: "Snapshot head changed during restore.", expectedVersion, actualVersion: currentVersion }, { status: 409 });
    const source = await getVersion(datasetKey, restoredVersion);
    if (!source) return Response.json({ error: "Version not found." }, { status: 404 });
    const sourceManifest = getVersionManifest(source);
    const restoredBody = await getSnapshotBody(source.object_key);
    if (datasetKey === "bond-yields") validateSnapshot(datasetKey, restoredBody);
    const currentBody = current ? await getSnapshotBody(current.object_key) : null;
    const changeSet = collectChanges(datasetKey, currentBody, restoredBody);
    const version = (currentVersion ?? 0) + 1;
    const now = new Date().toISOString();
    const diffText = JSON.stringify({ datasetKey, version, createdAt: now, restoredFromVersion: restoredVersion, changes: changeSet.all });
    const diffHash = await sha256(diffText);
    const diffObjectKey = `snapshots/${datasetKey}/v${version}/restore-${diffHash}.json`;
    await getBucket().put(diffObjectKey, diffText, { httpMetadata: { contentType: "application/json; charset=utf-8" } });
    const chartAssets: Array<{ period: string; country: string; sha256: string; objectKey: string }> = [];
    if (datasetKey === "bond-yields") {
      const artifacts = renderBondChartAssets(restoredBody as BondSnapshot, version, source.snapshot_sha256);
      for (const artifact of artifacts) {
        const digest = await sha256(artifact.svg);
        await getBucket().put(artifact.objectKey, artifact.svg, { httpMetadata: { contentType: "image/svg+xml; charset=utf-8", cacheControl: "private, max-age=31536000, immutable" } });
        chartAssets.push({ period: artifact.period, country: artifact.country, sha256: digest, objectKey: artifact.objectKey });
      }
    }
    const manifest = {
      changeCount: changeSet.all.length,
      recentChangeCount: changeSet.recentCount,
      diffObjectKey,
      rawSnapshots: sourceManifest.rawSnapshots,
      chartAssets,
      sourceStatus: sourceManifest.sourceStatus,
      summary: { ...sourceManifest.summary, restoredFromVersion: restoredVersion },
    };
    const db = getDatabase();
    try {
      await db.batch([
        db.prepare(
          `INSERT INTO snapshot_versions (dataset_key, version, object_key, snapshot_sha256, manifest_json, previous_version, restored_from_version, created_at, created_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'site-owner')`,
        ).bind(datasetKey, version, source.object_key, source.snapshot_sha256, JSON.stringify(manifest), currentVersion, restoredVersion, now),
        db.prepare(
          `INSERT INTO snapshot_diffs (dataset_key, version, diff_object_key, change_count, recent_change_count, observed_at)
           VALUES (?, ?, ?, ?, ?, ?)`,
        ).bind(datasetKey, version, diffObjectKey, changeSet.all.length, changeSet.recentCount, now),
        db.prepare(
          `INSERT INTO snapshot_heads (dataset_key, version, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(dataset_key) DO UPDATE SET version = excluded.version, updated_at = excluded.updated_at`,
        ).bind(datasetKey, version, now),
      ]);
    } catch (error) {
      const latest = await getCurrentVersion(datasetKey).catch(() => null);
      const actualVersion = latest?.version ?? null;
      if (actualVersion !== currentVersion) {
        return Response.json({ error: "Snapshot head changed during restore.", expectedVersion: currentVersion, actualVersion }, { status: 409 });
      }
      throw error;
    }
    return Response.json({ datasetKey, version, restoredFromVersion: restoredVersion, snapshotSha256: source.snapshot_sha256, changeCount: changeSet.all.length, ...(datasetKey !== "bond-yields" || isLocalBondDataAccessEnabled() ? { restoredBody } : {}) }, { status: 201, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Restore failed; the current snapshot remains unchanged." }, { status: 503 });
  }
}
