import { getSnapshotBody, getVersion, getVersionManifest, isSnapshotDataset } from "@/lib/snapshots";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ datasetKey: string; version: string }> }) {
  const { datasetKey, version: versionText } = await context.params;
  if (!isSnapshotDataset(datasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  const version = Number(versionText);
  if (!Number.isInteger(version) || version < 1) return Response.json({ error: "Invalid version." }, { status: 400 });
  try {
    const row = await getVersion(datasetKey, version);
    if (!row) return Response.json({ error: "Version not found." }, { status: 404 });
    const manifest = getVersionManifest(row);
    const object = await getSnapshotBody(manifest.diffObjectKey);
    if (datasetKey === "bond-yields" && !isLocalBondDataAccessEnabled()) {
      const full = object && typeof object === "object" ? object as Record<string, unknown> : {};
      const changes = Array.isArray(full.changes) ? full.changes : [];
      return Response.json({ datasetKey, version, manifest, diff: { datasetKey, version, createdAt: full.createdAt, changeCount: changes.length, summaryOnly: true } }, { headers: { "Cache-Control": "private, no-store" } });
    }
    return Response.json({ datasetKey, version, diff: object, manifest }, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Revision diff is unavailable." }, { status: 503 });
  }
}
