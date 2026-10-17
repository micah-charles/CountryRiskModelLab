import { BOND_COUNTRIES, type BondSnapshot, type CountryKey, type YieldPoint } from "../app/data/catalog.ts";

export const BOND_CHART_PRESETS = [
  { key: "last-3-years", label: "Last 3 years", years: 3 },
  { key: "last-1-year", label: "Last 1 year", years: 1 },
  { key: "year-to-date", label: "Year to date", years: null },
  { key: "last-5-years", label: "Last 5 years", years: 5 },
  { key: "since-2020", label: "2020–present", years: null },
] as const;

export type BondChartPresetKey = (typeof BOND_CHART_PRESETS)[number]["key"];
export type BondChartAssetInput = {
  period: BondChartPresetKey;
  country: "base" | CountryKey;
  objectKey: string;
  svg: string;
};

const WIDTH = 1920;
const HEIGHT = 1080;
const LEFT = 132;
const RIGHT = 1848;
const TOP = 186;
const BOTTOM = 834;

/** Render static SVG artifacts from a validated snapshot; raw observations never reach the UI. */
export function renderBondChartAssets(snapshot: BondSnapshot, version: number, snapshotSha256: string): BondChartAssetInput[] {
  const available = BOND_COUNTRIES.filter((country) => Array.isArray(snapshot.series[country.key]) && snapshot.series[country.key]!.length > 0);
  const allPoints = available.flatMap((country) => snapshot.series[country.key] ?? []);
  if (!available.length || !allPoints.length) throw new Error("Cannot make bond charts from an empty snapshot.");
  const endDate = allPoints.reduce((latest, point) => point.date > latest ? point.date : latest, "2020-01-01");
  const root = `snapshots/bond-yields/v${version}/${snapshotSha256}/charts`;
  const assets: BondChartAssetInput[] = [];

  for (const preset of BOND_CHART_PRESETS) {
    const startDate = periodStart(preset.key, preset.years, endDate);
    const series = new Map<CountryKey, YieldPoint[]>(available.map(({ key }) => [key, (snapshot.series[key] ?? []).filter((point) => point.date >= startDate && point.date <= endDate)]));
    const values = [...series.values()].flatMap((rows) => rows.flatMap((row) => row.value === null ? [] : [row.value]));
    if (!values.length) throw new Error(`No bond observations are available for the ${preset.label} chart.`);
    const { min, max, step } = rangeFor(values);
    const coordinates = makeCoordinates(startDate, endDate, min, max, series);
    const prefix = `${root}/${preset.key}`;
    assets.push({ period: preset.key, country: "base", objectKey: `${prefix}/base.svg`, svg: baseSvg(snapshot, preset.label, startDate, endDate, version, available, coordinates, min, max, step) });
    for (const country of available) {
      assets.push({ period: preset.key, country: country.key, objectKey: `${prefix}/${country.key}.svg`, svg: seriesSvg(country.key, coordinates.paths[country.key] ?? "", coordinates.lastPoints[country.key]) });
    }
  }
  return assets;
}

function periodStart(key: BondChartPresetKey, years: number | null, endDate: string) {
  if (key === "since-2020") return "2020-01-01";
  if (key === "year-to-date") return `${endDate.slice(0, 4)}-01-01`;
  const date = new Date(`${endDate}T00:00:00.000Z`);
  date.setUTCFullYear(date.getUTCFullYear() - (years ?? 1));
  return date.toISOString().slice(0, 10);
}

function rangeFor(values: number[]) {
  const low = Math.min(...values), high = Math.max(...values);
  const padding = Math.max((high - low) * 0.08, 0.15);
  const step = niceStep((high - low + padding * 2) / 5);
  const min = Math.floor((low - padding) / step) * step;
  const max = Math.ceil((high + padding) / step) * step;
  return { min, max: max > min ? max : min + step, step };
}

function niceStep(value: number) {
  const power = Math.pow(10, Math.floor(Math.log10(Math.max(value, 0.05))));
  const normalized = value / power;
  const multiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 2.5 ? 2.5 : normalized <= 5 ? 5 : 10;
  return multiplier * power;
}

function makeCoordinates(start: string, end: string, min: number, max: number, series: Map<CountryKey, YieldPoint[]>) {
  const startMs = Date.parse(`${start}T00:00:00Z`), endMs = Date.parse(`${end}T00:00:00Z`);
  const width = RIGHT - LEFT, height = BOTTOM - TOP;
  const x = (date: string) => LEFT + (endMs === startMs ? width : ((Date.parse(`${date}T00:00:00Z`) - startMs) / (endMs - startMs)) * width);
  const y = (value: number) => BOTTOM - ((value - min) / (max - min)) * height;
  const paths: Partial<Record<CountryKey, string>> = {};
  const lastPoints: Partial<Record<CountryKey, { x: number; y: number; date: string; value: number }>> = {};
  for (const [country, rows] of series) {
    let path = "", penDown = false;
    for (const point of rows) {
      if (point.value === null) { penDown = false; continue; }
      const px = x(point.date), py = y(point.value);
      path += `${penDown ? "L" : "M"}${px.toFixed(2)},${py.toFixed(2)} `;
      penDown = true;
      lastPoints[country] = { x: px, y: py, date: point.date, value: point.value };
    }
    paths[country] = path.trim();
  }
  return { paths, lastPoints, x, y };
}

function baseSvg(snapshot: BondSnapshot, label: string, start: string, end: string, version: number, countries: typeof BOND_COUNTRIES, coordinates: ReturnType<typeof makeCoordinates>, min: number, max: number, step: number) {
  const ticks: number[] = [];
  for (let value = min; value <= max + step * 0.01; value += step) ticks.push(Number(value.toFixed(6)));
  const grid = ticks.map((value) => {
    const y = coordinates.y(value);
    return `<g><line x1="${LEFT}" x2="${RIGHT}" y1="${y.toFixed(2)}" y2="${y.toFixed(2)}" stroke="#e7ece8"/><text x="${LEFT - 14}" y="${(y + 8).toFixed(2)}" text-anchor="end" font-size="23" fill="#738078">${value.toFixed(2)}%</text></g>`;
  }).join("");
  const xLabels = Array.from({ length: 6 }, (_, index) => {
    const date = new Date(Date.parse(`${start}T00:00:00Z`) + (Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) * index / 5);
    const dateText = date.toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
    const x = LEFT + (RIGHT - LEFT) * index / 5;
    return `<g><line x1="${x.toFixed(2)}" x2="${x.toFixed(2)}" y1="${BOTTOM}" y2="${BOTTOM + 8}" stroke="#adb8b1"/><text x="${x.toFixed(2)}" y="${BOTTOM + 38}" text-anchor="${index === 0 ? "start" : index === 5 ? "end" : "middle"}" font-size="21" fill="#738078">${escapeXml(dateText)}</text></g>`;
  }).join("");
  const legend = countries.map((country, index) => {
    const x = LEFT + (index % 3) * 570;
    const y = 143 + Math.floor(index / 3) * 30;
    const dash = country.key === "France" || country.key === "Italy" ? ` stroke-dasharray="8 6"` : country.key === "US" ? ` stroke-dasharray="2 7"` : "";
    return `<g><line x1="${x}" x2="${x + 42}" y1="${y}" y2="${y}" stroke="${country.color}" stroke-width="5"${dash}/><text x="${x + 55}" y="${y + 8}" font-size="21" fill="#33473e">${escapeXml(country.name)}</text></g>`;
  }).join("");
  const sourceLines = countries.map((country, index) => {
    const source = snapshot.sources?.[country.key];
    const status = snapshot.sourceStatus?.[country.key]?.status ?? "not stated";
    const line = `${country.name}: ${source?.agency ?? country.agency} · ${source?.seriesId ?? "series ID unavailable"} · ${status}`;
    const x = index < 3 ? LEFT : 1010;
    const y = 936 + (index % 3) * 22;
    return `<text x="${x}" y="${y}" font-size="15" fill="#5e7067">${escapeXml(line)}</text>`;
  }).join("");
  const retrieved = escapeXml(snapshot.retrievedAt);
  const purpose = snapshot.operatorSelectedPurpose === "personal-interview";
  const purposeNotice = purpose
    ? `<text x="${LEFT}" y="1011" font-size="15" fill="#62736a">Operator-selected purpose: personal interview. Intended use only; this is not a rights determination.</text><text x="${LEFT}" y="1031" font-size="15" fill="#62736a">Euronext and Banca d’Italia terms apply; written permission not verified. Italy BMK0200 upstream vendors are not itemized.</text>`
    : "";
  return `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" aria-labelledby="title desc"><title id="title">Government bond yields · ${escapeXml(label)}</title><desc id="desc">Published 10-year government bond yield observations from ${escapeXml(start)} through ${escapeXml(end)}. Missing observations remain blank. ${purpose ? "Operator-selected personal-interview purpose is not a rights determination. Euronext and Banca d’Italia terms apply; written permission is not verified." : ""}</desc><rect width="${WIDTH}" height="${HEIGHT}" fill="#fff"/><g font-family="Arial, Helvetica, sans-serif"><text x="${LEFT}" y="63" font-size="37" font-weight="700" fill="#243a30">Government bond yields · 10-year benchmarks</text><text x="${LEFT}" y="102" font-size="23" fill="#6f7e75">${escapeXml(label)} · ${escapeXml(start)} to ${escapeXml(end)} · percent per annum</text>${legend}${grid}<line x1="${LEFT}" x2="${RIGHT}" y1="${BOTTOM}" y2="${BOTTOM}" stroke="#aeb9b2" stroke-width="2"/>${xLabels}<text x="31" y="520" transform="rotate(-90 31 520)" font-size="20" fill="#607168">Yield (%)</text><text x="${LEFT}" y="911" font-size="16" fill="#54665c">Sources and status · definitions differ by country</text>${sourceLines}${purposeNotice}<text x="${LEFT}" y="1055" font-size="15" fill="#62736a">Retrieved ${retrieved} · snapshot v${version} · Missing observations remain blank; no filling or interpolation.</text></g></svg>`;
}

function seriesSvg(country: CountryKey, path: string, last?: { x: number; y: number; date: string; value: number }) {
  const definition = BOND_COUNTRIES.find((item) => item.key === country)!;
  const dash = country === "France" || country === "Italy" ? ` stroke-dasharray="8 6"` : country === "US" ? ` stroke-dasharray="2 7"` : "";
  const marker = last ? `<circle cx="${last.x.toFixed(2)}" cy="${last.y.toFixed(2)}" r="7" fill="${definition.color}"/><circle cx="${last.x.toFixed(2)}" cy="${last.y.toFixed(2)}" r="12" fill="none" stroke="#fff" stroke-width="3"/>` : "";
  return `<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" aria-label="${escapeXml(definition.name)} yield curve"><g fill="none" stroke="${definition.color}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"${dash}><path d="${path}"/></g>${marker}</svg>`;
}

function escapeXml(value: unknown) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}
