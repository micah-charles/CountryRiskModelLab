import { BOND_CHART_PRESETS } from "@/lib/bond-chart-assets";
import { bondExportCsv, bondExportJson, bondExportXlsx, type BondExportPeriod } from "@/lib/bond-data-export";
import { getCurrentVersion, getSnapshotBody, getVersion } from "@/lib/snapshots";
import { ALL_BOND_COUNTRIES, validateSnapshot as validateSnapshotCore } from "@/lib/snapshot-logic";
import type { BondSnapshot } from "@/app/data/catalog";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  if (request.headers.get("sec-fetch-site") === "cross-site") {
    return exportError("Cross-site data exports are forbidden.", 403);
  }
  const origin = request.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).origin !== new URL(request.url).origin) {
        return exportError("Cross-site data exports are forbidden.", 403);
      }
    } catch {
      return exportError("Invalid request origin.", 403);
    }
  }

  const params = new URL(request.url).searchParams;
  const requestedVersion = params.get("version");
  const format = params.get("format") ?? "csv";
  const periodText = params.get("period") ?? "last-3-years";
  if (!(["csv", "json", "xlsx"] as const).includes(format as "csv" | "json" | "xlsx")) {
    return exportError("format must be csv, json, or xlsx.", 400);
  }
  const period = periodText === "full" || BOND_CHART_PRESETS.some((preset) => preset.key === periodText)
    ? periodText as BondExportPeriod
    : null;
  if (!period) return exportError("Unknown bond chart period.", 400);
  if (requestedVersion !== null && (!/^\d+$/.test(requestedVersion) || Number(requestedVersion) < 1)) {
    return exportError("version must be a positive integer.", 400);
  }

  try {
    const row = requestedVersion === null
      ? await getCurrentVersion("bond-yields")
      : await getVersion("bond-yields", Number(requestedVersion));
    if (!row) return exportError("Bond snapshot version not found.", 404);
    const snapshot = await getSnapshotBody(row.object_key) as BondSnapshot;
    const availableCountries = Object.keys(snapshot.series ?? {});
    if (!availableCountries.length || availableCountries.some((country) => !(ALL_BOND_COUNTRIES as readonly string[]).includes(country))) {
      return exportError("Stored bond snapshot has unsupported country coverage.", 409);
    }
    validateSnapshotCore("bond-yields", snapshot, availableCountries);
    const context = { version: row.version, snapshotSha256: row.snapshot_sha256, createdAt: row.created_at };
    const filePeriod = period === "full" ? "full-history" : period;
    const filename = `government-bond-yields-v${row.version}-${filePeriod}`;
    const headers = {
      "Cache-Control": "private, no-store",
      "Content-Disposition": `attachment; filename="${filename}.${format}"`,
      "X-Content-Type-Options": "nosniff",
    };

    if (format === "json") return new Response(bondExportJson(snapshot, context, period), { headers: { ...headers, "Content-Type": "application/json; charset=utf-8" } });
    if (format === "xlsx") {
      const workbook = bondExportXlsx(snapshot, context, period);
      const workbookBody = workbook.buffer.slice(workbook.byteOffset, workbook.byteOffset + workbook.byteLength) as ArrayBuffer;
      return new Response(workbookBody, { headers: { ...headers, "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" } });
    }
    return new Response(bondExportCsv(snapshot, context, period), { headers: { ...headers, "Content-Type": "text/csv; charset=utf-8" } });
  } catch (error) {
    return exportError(error instanceof Error ? error.message : "Bond data export failed.", 503);
  }
}

function exportError(message: string, status: number) {
  return Response.json({ error: message }, { status, headers: { "Cache-Control": "private, no-store" } });
}
