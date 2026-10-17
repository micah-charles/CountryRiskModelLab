import { isSnapshotDataset, listVersions } from "@/lib/snapshots";

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: { params: Promise<{ datasetKey: string }> }) {
  const { datasetKey } = await context.params;
  if (!isSnapshotDataset(datasetKey)) return Response.json({ error: "Unknown snapshot dataset." }, { status: 404 });
  const limit = Number(new URL(request.url).searchParams.get("limit") ?? "100");
  try {
    return Response.json({ datasetKey, versions: await listVersions(datasetKey, limit) }, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Version history is unavailable." }, { status: 503 });
  }
}
