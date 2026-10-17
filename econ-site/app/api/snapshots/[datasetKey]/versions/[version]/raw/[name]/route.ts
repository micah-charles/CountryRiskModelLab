import { getBucket, getVersion, getVersionManifest, isSnapshotDataset } from "@/lib/snapshots";
import { isLocalBondDataAccessEnabled } from "@/lib/site-config";

export const dynamic = "force-dynamic";

export async function GET(_request: Request, context: { params: Promise<{ datasetKey: string; version: string; name: string }> }) {
  const { datasetKey, version: versionText, name } = await context.params;
  if (!isSnapshotDataset(datasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  if (datasetKey === "bond-yields" && !isLocalBondDataAccessEnabled()) return Response.json({ error: "Raw bond source downloads are available only from the local workspace." }, { status: 404 });
  const version = Number(versionText);
  if (!Number.isInteger(version) || version < 1) return Response.json({ error: "Invalid version." }, { status: 400 });
  try {
    const row = await getVersion(datasetKey, version);
    if (!row) return Response.json({ error: "Version not found." }, { status: 404 });
    const item = getVersionManifest(row).rawSnapshots.find((candidate) => candidate.name === name);
    if (!item) return Response.json({ error: "Raw source snapshot not found." }, { status: 404 });
    const object = await getBucket().get(item.objectKey);
    if (!object) return Response.json({ error: "Raw source snapshot is missing." }, { status: 404 });
    return new Response(object.body, {
      headers: {
        "Content-Type": name.endsWith(".zip") ? "application/zip" : "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="${name.replace(/[^A-Za-z0-9._-]/g, "_")}"`,
        "Cache-Control": "private, no-store",
        "X-Source-SHA256": item.sha256,
      },
    });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Raw snapshot is unavailable." }, { status: 503 });
  }
}
