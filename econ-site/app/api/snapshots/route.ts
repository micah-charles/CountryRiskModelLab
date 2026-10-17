import { getDatabase, isSnapshotDataset, toVersionManifest } from "@/lib/snapshots";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const rows = await getDatabase().prepare(
      `SELECT v.dataset_key, v.version, v.object_key, v.snapshot_sha256, v.manifest_json,
              v.previous_version, v.restored_from_version, v.created_at, v.created_by
       FROM snapshot_heads h
       JOIN snapshot_versions v ON v.dataset_key = h.dataset_key AND v.version = h.version
       ORDER BY v.dataset_key`,
    ).all();
    const snapshots = (rows.results ?? []).flatMap((raw) => {
      const row = raw as Parameters<typeof toVersionManifest>[0];
      return isSnapshotDataset(row.dataset_key) ? [toVersionManifest(row)] : [];
    });
    return Response.json({ snapshots }, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Snapshot catalog is unavailable." }, { status: 503 });
  }
}
