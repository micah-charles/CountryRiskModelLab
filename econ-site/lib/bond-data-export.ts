import { strToU8, zipSync } from "fflate";
import { BOND_CHART_PRESETS } from "./bond-chart-logic.ts";
import { resolveBondPeriodBounds, type BondDateGrid, type BondPeriodMode } from "./bond-chart-logic.ts";
import { BOND_COUNTRIES, type BondSnapshot, type CountryKey, type SourceDetails, type YieldPoint } from "../app/data/catalog.ts";

export type BondExportPeriod = "full" | (typeof BOND_CHART_PRESETS)[number]["key"];
export type BondExportContext = { version: number; snapshotSha256: string; createdAt: string };

export type BondExportOptions = { periodMode?: BondPeriodMode; dateGrid?: BondDateGrid; countries?: CountryKey[] };

export function prepareBondExport(snapshot: BondSnapshot, context: BondExportContext, period: BondExportPeriod, options: BondExportOptions = {}) {
  const allDates = Object.values(snapshot.series).flatMap((rows) => (rows ?? []).map((row) => row.date)).sort();
  if (!allDates.length) throw new Error("The selected snapshot contains no bond observations.");
  const endDate = allDates.at(-1)!;
  const bounds = period === "full"
    ? { startDate: snapshot.periodStart, endDate, mode: "fixed" as const }
    : resolveBondPeriodBounds(period, options.periodMode ?? "rolling", endDate);
  const startDate = bounds.startDate;
  const available = BOND_COUNTRIES.map(({ key }) => key).filter((key) => Array.isArray(snapshot.series[key]) && snapshot.series[key]!.length > 0);
  const requested = options.countries;
  if (requested && (new Set(requested).size !== requested.length || requested.some((key) => !available.includes(key)))) {
    throw new Error("Selected chart countries must be unique and available in this snapshot.");
  }
  const countries = requested ? BOND_COUNTRIES.map(({ key }) => key).filter((key) => requested.includes(key) && available.includes(key)) : available;
  if (!countries.length) throw new Error("Choose at least one country available in this snapshot.");
  const series = Object.fromEntries(countries.map((country) => [country, snapshot.series[country]!.filter((row) => row.date >= startDate && row.date <= endDate)])) as Partial<Record<CountryKey, YieldPoint[]>>;
  const dates = [...new Set(Object.values(series).flatMap((rows) => rows?.map((row) => row.date) ?? []))].sort();
  const valuesByCountry = new Map<CountryKey, Map<string, number | null>>();
  for (const country of countries) valuesByCountry.set(country, new Map((series[country] ?? []).map((row) => [row.date, row.value])));
  const observationCount = countries.reduce((sum, country) => sum + (series[country]?.length ?? 0), 0);
  const sources = Object.fromEntries(countries.map((country) => [country, snapshot.sources[country]])) as Partial<Record<CountryKey, SourceDetails>>;
  const sourceStatus = Object.fromEntries(countries.map((country) => [country, snapshot.sourceStatus?.[country]]));
  const metadata = {
    datasetKey: "bond-yields",
    version: context.version,
    snapshotSha256: context.snapshotSha256,
    snapshotCreatedAt: context.createdAt,
    retrievedAt: snapshot.retrievedAt,
    period,
    periodMode: bounds.mode,
    dateGrid: options.dateGrid ?? "quarterly",
    periodStart: startDate,
    periodEnd: endDate,
    operatorSelectedPurpose: snapshot.operatorSelectedPurpose ?? null,
    sourceRightsStatus: snapshot.sourceRightsStatus ?? {},
    downloadAccessNote: "Owner-only downloads read this immutable stored snapshot; downloading does not refresh data or change the current snapshot.",
    missingValuePolicy: snapshot.missingValuePolicy,
    historyComplete: snapshot.historyComplete,
    observationCount,
    dateCount: dates.length,
    sources,
    sourceStatus,
  };
  return { period, startDate, endDate, countries, dates, series, valuesByCountry, metadata };
}

export function bondExportJson(snapshot: BondSnapshot, context: BondExportContext, period: BondExportPeriod, options: BondExportOptions = {}) {
  const prepared = prepareBondExport(snapshot, context, period, options);
  const exportObject = {
    ...prepared.metadata,
    restrictedCountries: snapshot.restrictedCountries ?? [],
    note: snapshot.note ?? "",
    series: prepared.series,
  };
  return JSON.stringify(exportObject, null, 2);
}

export function bondExportCsv(snapshot: BondSnapshot, context: BondExportContext, period: BondExportPeriod, options: BondExportOptions = {}) {
  const prepared = prepareBondExport(snapshot, context, period, options);
  const lines = [
    `# snapshot_version=${prepared.metadata.version}`,
    `# snapshot_sha256=${prepared.metadata.snapshotSha256}`,
    `# snapshot_created_at=${prepared.metadata.snapshotCreatedAt}`,
    `# retrieved_at=${prepared.metadata.retrievedAt}`,
    `# period=${prepared.period}; mode=${prepared.metadata.periodMode}; date_grid=${prepared.metadata.dateGrid}; start=${prepared.startDate}; end=${prepared.endDate}`,
    `# operator_selected_purpose=${prepared.metadata.operatorSelectedPurpose ?? "not-recorded"}`,
    `# source_rights_status=${JSON.stringify(prepared.metadata.sourceRightsStatus)}`,
    `# download_access=${prepared.metadata.downloadAccessNote}`,
    `# snapshot_note_at_retrieval=${JSON.stringify(snapshot.note ?? "")}`,
    `# missing_value_policy=${prepared.metadata.missingValuePolicy}; gaps remain blank; no filling or interpolation`,
  ];
  for (const country of prepared.countries) {
    const source = prepared.metadata.sources[country];
    const status = prepared.metadata.sourceStatus[country];
    lines.push(`# source=${JSON.stringify({ country, ...source, status })}`);
  }
  lines.push(["Date", ...prepared.countries].join(","));
  for (const date of prepared.dates) {
    lines.push([date, ...prepared.countries.map((country) => {
      const value = prepared.valuesByCountry.get(country)?.get(date);
      return value === null || value === undefined ? "" : String(value);
    })].join(","));
  }
  return lines.join("\r\n");
}

export function bondExportXlsx(snapshot: BondSnapshot, context: BondExportContext, period: BondExportPeriod, options: BondExportOptions = {}): Uint8Array {
  const prepared = prepareBondExport(snapshot, context, period, options);
  const dataRows: Array<Array<string | number>> = [["Date", ...prepared.countries]];
  for (const date of prepared.dates) {
    dataRows.push([date, ...prepared.countries.map((country) => {
      const value = prepared.valuesByCountry.get(country)?.get(date);
      return value === null || value === undefined ? "" : value;
    })]);
  }

  const sourceRows: Array<Array<string | number>> = [["Country", "Agency", "Series ID", "Definition", "Unit", "Frequency", "Source URL", "Reuse note", "Source status", "Observation count", "First observation", "Latest observation", "Rights status"]];
  for (const country of prepared.countries) {
    const source = prepared.metadata.sources[country];
    const rows = prepared.series[country] ?? [];
    sourceRows.push([
      country,
      source?.agency ?? "",
      source?.seriesId ?? "",
      source?.definition ?? "",
      source?.unit ?? "",
      source?.frequency ?? "",
      source?.sourceUrl ?? "",
      source?.reuse ?? "",
      String(prepared.metadata.sourceStatus[country]?.status ?? "not stated"),
      rows.length,
      rows[0]?.date ?? "",
      rows.at(-1)?.date ?? "",
      snapshot.sourceRightsStatus?.[country] ?? "not applicable",
    ]);
  }
  const snapshotRows: Array<Array<string | number>> = [
    ["Field", "Value"],
    ["Dataset", "bond-yields"],
    ["Snapshot version", prepared.metadata.version],
    ["Snapshot SHA-256", prepared.metadata.snapshotSha256],
    ["Snapshot created at", prepared.metadata.snapshotCreatedAt],
    ["Sources retrieved at", prepared.metadata.retrievedAt],
    ["Export period", prepared.period],
    ["Period mode", prepared.metadata.periodMode],
    ["Date grid", prepared.metadata.dateGrid],
    ["Period start", prepared.startDate],
    ["Period end", prepared.endDate],
    ["Operator-selected purpose", prepared.metadata.operatorSelectedPurpose ?? "not recorded"],
    ["Source rights status", JSON.stringify(prepared.metadata.sourceRightsStatus)],
    ["Download access", prepared.metadata.downloadAccessNote],
    ["Missing value policy", "blank-no-fill"],
    ["History complete", snapshot.historyComplete ? "yes" : "no"],
    ["Observation rows", prepared.metadata.observationCount],
    ["Date rows", prepared.dates.length],
    ["Snapshot note recorded at retrieval", snapshot.note ?? ""],
  ];
  const files: Record<string, Uint8Array> = {
    "[Content_Types].xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>`),
    "_rels/.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`),
    "xl/workbook.xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Yield observations" sheetId="1" r:id="rId1"/><sheet name="Sources &amp; notes" sheetId="2" r:id="rId2"/><sheet name="Snapshot" sheetId="3" r:id="rId3"/></sheets></workbook>`),
    "xl/_rels/workbook.xml.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/></Relationships>`),
    "xl/worksheets/sheet1.xml": strToU8(sheetXml(dataRows)),
    "xl/worksheets/sheet2.xml": strToU8(sheetXml(sourceRows)),
    "xl/worksheets/sheet3.xml": strToU8(sheetXml(snapshotRows)),
  };
  return zipSync(files, { level: 6 });
}

function sheetXml(rows: Array<Array<string | number>>) {
  const cell = (value: string | number | null | undefined, row: number, column: number) => {
    const address = `${columnName(column)}${row}`;
    if (value === "" || value === null || value === undefined) return "";
    if (typeof value === "number") return `<c r="${address}"><v>${value}</v></c>`;
    const escaped = xmlEscape(value);
    return `<c r="${address}" t="inlineStr"><is><t xml:space="preserve">${escaped}</t></is></c>`;
  };
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${rows.map((row, index) => `<row r="${index + 1}">${row.map((value, column) => cell(value, index + 1, column + 1)).join("")}</row>`).join("")}</sheetData></worksheet>`;
}

function columnName(value: number) {
  let name = "";
  while (value) { const remainder = (value - 1) % 26; name = String.fromCharCode(65 + remainder) + name; value = Math.floor((value - 1) / 26); }
  return name;
}

function xmlEscape(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
}
