import { BOND_CHART_PRESETS } from "@/lib/bond-chart-assets";
import { getBucket, getCurrentVersion, getHostedBondCountries, getVersion, getVersionManifest, sha256 } from "@/lib/snapshots";
import { isCountryKey, type CountryKey } from "@/app/data/catalog";

export const dynamic = "force-dynamic";

/** Serves a stored SVG artifact only; this route never serializes daily observations. */
export async function GET(request: Request, context: { params: Promise<{ period: string; asset: string }> }) {
  const { period, asset } = await context.params;
  if (!BOND_CHART_PRESETS.some((item) => item.key === period)) return Response.json({ error: "Unknown chart period." }, { status: 404 });
  const country = asset === "base.svg" ? "base" : asset.endsWith(".svg") ? asset.slice(0, -4) : "";
  if (country !== "base" && !isCountryKey(country)) return Response.json({ error: "Unknown chart asset." }, { status: 404 });
  const allowedCountries = new Set(getHostedBondCountries());
  if (country !== "base" && !allowedCountries.has(country as CountryKey)) return Response.json({ error: "This chart is not enabled for hosted display." }, { status: 404 });
  const versionText = new URL(request.url).searchParams.get("v");
  const version = versionText === null ? null : Number(versionText);
  if (versionText !== null && (!Number.isInteger(version) || version! < 1)) return Response.json({ error: "Invalid snapshot version." }, { status: 400 });
  try {
    const row = version === null ? await getCurrentVersion("bond-yields") : await getVersion("bond-yields", version);
    if (!row) return Response.json({ error: "Bond chart version not found." }, { status: 404 });
    const manifest = getVersionManifest(row);
    const periodAssets = (manifest.chartAssets ?? []).filter((candidate) => candidate.period === period);
    if (periodAssets.some((candidate) => candidate.country !== "base" && !allowedCountries.has(candidate.country as CountryKey))) {
      return Response.json({ error: "This chart includes a country that is not currently enabled for hosted display." }, { status: 404 });
    }
    const item = periodAssets.find((candidate) => candidate.country === country);
    if (!item || !item.objectKey.startsWith(`snapshots/bond-yields/v${row.version}/${row.snapshot_sha256}/charts/`)) {
      return Response.json({ error: "Prepared chart image is not available for this version." }, { status: 404 });
    }
    const object = await getBucket().get(item.objectKey);
    if (!object) return Response.json({ error: "Prepared chart image is missing." }, { status: 404 });
    const svg = await object.text();
    if (await sha256(svg) !== item.sha256) return Response.json({ error: "Prepared chart image failed its integrity check." }, { status: 503 });
    return new Response(svg, { headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": version === null ? "private, no-store" : "private, max-age=31536000, immutable",
      "X-Bond-Snapshot-Version": String(row.version),
      "X-Chart-Asset-SHA256": item.sha256,
      "X-Content-Type-Options": "nosniff",
    } });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "Prepared chart image is unavailable." }, { status: 503 });
  }
}
