import { BOND_CHART_PRESETS, type BondChartPresetKey } from "@/lib/bond-chart-logic";
import { resolveBondPeriodBounds, type BondPeriodMode } from "@/lib/bond-chart-logic";
import { getCurrentVersion, getSnapshotBody, getVersion } from "@/lib/snapshots";
import { ALL_BOND_COUNTRIES, validateSnapshot as validateSnapshotCore } from "@/lib/snapshot-logic";
import type { BondSnapshot } from "@/app/data/catalog";

export const dynamic = "force-dynamic";

/** Daily observations are returned only through the existing owner-private Site audience. */
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const periodText = params.get("period") ?? "last-3-years";
  const modeText = params.get("mode") ?? "rolling";
  const versionText = params.get("version");
  const period = BOND_CHART_PRESETS.find((item) => item.key === periodText)?.key as BondChartPresetKey | undefined;
  if (!period) return error("Unknown chart period.", 400);
  if (modeText !== "rolling" && modeText !== "calendar") return error("mode must be rolling or calendar.", 400);
  if (versionText !== null && (!/^\d+$/.test(versionText) || Number(versionText) < 1)) return error("version must be a positive integer.", 400);
  try {
    const row = versionText === null ? await getCurrentVersion("bond-yields") : await getVersion("bond-yields", Number(versionText));
    if (!row) return error("Bond snapshot version not found.", 404);
    const snapshot = await getSnapshotBody(row.object_key) as BondSnapshot;
    const availableCountries = Object.keys(snapshot.series ?? {});
    if (!availableCountries.length || availableCountries.some((country) => !(ALL_BOND_COUNTRIES as readonly string[]).includes(country))) {
      return error("Stored bond snapshot has unsupported country coverage.", 409);
    }
    validateSnapshotCore("bond-yields", snapshot, availableCountries);
    const dates = Object.values(snapshot.series).flatMap((points) => (points ?? []).map((point) => point.date)).sort();
    if (!dates.length) return error("Bond snapshot contains no observations.", 409);
    const endDate = dates.at(-1)!;
    const bounds = resolveBondPeriodBounds(period, modeText as BondPeriodMode, endDate);
    const series = Object.fromEntries(availableCountries.map((country) => [country, snapshot.series[country as keyof typeof snapshot.series]!.filter((point) => point.date >= bounds.startDate && point.date <= bounds.endDate)]));
    return Response.json({
      datasetKey: "bond-yields",
      version: row.version,
      period,
      periodMode: bounds.mode,
      startDate: bounds.startDate,
      endDate: bounds.endDate,
      retrievedAt: snapshot.retrievedAt,
      sources: snapshot.sources,
      series,
    }, { headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
  } catch (error) {
    return errorResponse(error instanceof Error ? error.message : "Bond observations could not be read.", 503);
  }
}

function error(message: string, status: number) {
  return errorResponse(message, status);
}

function errorResponse(message: string, status: number) {
  return Response.json({ error: message }, { status, headers: { "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff" } });
}
