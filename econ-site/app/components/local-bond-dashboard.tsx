"use client";

import { Download, FileSpreadsheet, ImageDown, Upload } from "lucide-react";
import { strToU8, zipSync } from "fflate";
import { useMemo, useRef, useState } from "react";
import { useSnapshot } from "@/app/components/snapshot-fetch";
import { BOND_COUNTRIES, BOND_SOURCE_DETAILS, type BondSnapshot, type CountryKey, type YieldPoint } from "@/app/data/catalog";
import { BOND_CHART_PRESETS, integerYieldDomain, resolveBondPeriodBounds, type BondChartPresetKey, type BondDateGrid, type BondPeriodMode } from "@/lib/bond-chart-logic";
import { BondYieldChart, exportBondChart } from "@/app/components/bond-yield-chart";

type RawEnvelope = { snapshot: BondSnapshot; version: number; manifest: Record<string, unknown> };
const HOSTED = new Set<CountryKey>(["US", "UK", "Germany", "Japan"]);
const COLORS = Object.fromEntries(BOND_COUNTRIES.map((country) => [country.key, country.color])) as Record<CountryKey, string>;

export function LocalBondDashboard() {
  const loaded = useSnapshot<BondSnapshot>("bond-yields");
  const envelope = loaded.value as (RawEnvelope | undefined);
  const snapshot = envelope?.snapshot;
  const [localSeries, setLocalSeries] = useState<Partial<Record<CountryKey, YieldPoint[]>>>({});
  const [localLabel, setLocalLabel] = useState("");
  const [selected, setSelected] = useState<CountryKey[]>(["US", "UK", "France", "Italy", "Germany", "Japan"]);
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("");
  const [periodPreset, setPeriodPreset] = useState<BondChartPresetKey | null>("since-2020");
  const [periodMode, setPeriodMode] = useState<BondPeriodMode>("rolling");
  const [dateGrid, setDateGrid] = useState<BondDateGrid>("quarterly");
  const [importError, setImportError] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const chartRef = useRef<SVGSVGElement>(null);
  const series = useMemo(() => ({ ...(snapshot?.series ?? {}), ...localSeries }), [snapshot, localSeries]);
  const allDates = useMemo(() => Object.values(series).flatMap((rows) => (rows ?? []).map((point) => point.date)).sort(), [series]);
  const minDate = allDates[0] ?? "2020-01-01";
  const maxDate = allDates.at(-1) ?? "";
  const effectiveEnd = endDate || maxDate;
  const invalidRange = Boolean(effectiveEnd && startDate > effectiveEnd);
  const filtered = useMemo(() => Object.fromEntries(BOND_COUNTRIES.map(({ key }) => [key, (series[key] ?? []).filter((point) => point.date >= startDate && point.date <= effectiveEnd)])) as Partial<Record<CountryKey, YieldPoint[]>>, [series, startDate, effectiveEnd]);
  const shownRows = selected.flatMap((country) => (filtered[country] ?? []).flatMap((point) => point.value === null ? [] : [{ date: point.date, country, value: point.value }]));
  const currentPreset = periodPreset ? BOND_CHART_PRESETS.find((item) => item.key === periodPreset) : null;
  const periodDescription = currentPreset?.years === null ? (periodPreset === "year-to-date" ? "Calendar year to date" : "Since 1 January 2020") : currentPreset ? `${periodMode === "rolling" ? "Rolling" : "Calendar-year"} ${currentPreset.years}-year window` : "Custom dates";

  function applyPeriod(preset: BondChartPresetKey, mode = periodMode) {
    if (!maxDate) return;
    const bounds = resolveBondPeriodBounds(preset, mode, maxDate);
    setPeriodPreset(preset);
    setStartDate(bounds.startDate);
    setEndDate(bounds.endDate);
  }

  function changePeriodMode(mode: BondPeriodMode) {
    setPeriodMode(mode);
    if (periodPreset) applyPeriod(periodPreset, mode);
  }

  async function importFile(file?: File) {
    if (!file) return;
    setImportError("");
    try {
      const text = await file.text();
      const parsed = file.name.toLowerCase().endsWith(".json") ? parseJsonSeries(JSON.parse(text)) : parseCsvSeries(text);
      if (!Object.keys(parsed).length) throw new Error("No recognized country/date/yield columns were found.");
      setLocalSeries(parsed);
      setLocalLabel(file.name);
      setPeriodPreset(null);
      setSelected(BOND_COUNTRIES.filter((country) => parsed[country.key] || HOSTED.has(country.key)).map((country) => country.key));
      const localDates = Object.values(parsed).flatMap((rows) => (rows ?? []).map((point) => point.date)).sort();
      if (localDates.length) { setStartDate(localDates[0]); setEndDate(localDates.at(-1) ?? ""); }
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "Could not read the selected file.");
    }
  }

  function toggle(country: CountryKey) {
    setSelected((current) => current.includes(country) ? current.filter((value) => value !== country) : [...current, country]);
  }

  async function exportChart(format: "svg" | "png") {
    if (!chartRef.current || !shownRows.length || invalidRange) return;
    const filePrefix = `government-bond-yields-${periodPreset ?? "custom"}-${periodMode}-${startDate}-${effectiveEnd}-${selected.join("-")}`;
    await exportBondChart(chartRef.current, format, filePrefix);
  }

  function exportWorkbook() {
    if (!shownRows.length || invalidRange) return;
    const dates = [...new Set(shownRows.map((row) => row.date))].sort();
    const dataRows: Array<Array<string | number>> = [["Date", ...selected.map((country) => country)]];
    for (const date of dates) dataRows.push([date, ...selected.map((country) => filtered[country]?.find((point) => point.date === date)?.value ?? "")]);
    const sourceRows: Array<Array<string | number>> = [["Country", "Agency", "Series", "Definition", "Source URL", "Reuse note", "Data origin / status", "Snapshot version", "Retrieved at"]];
    for (const country of selected) {
      const details = BOND_SOURCE_DETAILS[country];
      const status = localSeries[country] ? "local-file-unverified" : snapshot?.sourceStatus?.[country]?.status ?? "not loaded";
      const origin = localSeries[country] ? `Local file: ${localLabel}. Site did not validate provenance; the imported data was not uploaded.` : `Private cloud snapshot; ${status}.`;
      sourceRows.push([details.country, details.agency, details.seriesId, details.definition, details.sourceUrl, details.reuse, origin, localSeries[country] ? "Not applicable" : envelope?.version ?? "Not loaded", localSeries[country] ? "Not verified" : snapshot?.retrievedAt ?? ""]);
    }
    const lastRow = dates.length + 1;
    const chartDomain = integerYieldDomain(selected.flatMap((country) => (filtered[country] ?? []).flatMap((point) => point.value === null ? [] : [point.value])));
    const chartSeries = selected.map((country, index) => xlsxSeries(index, country, COLORS[country], countryDash(country)));
    const files: Record<string, Uint8Array> = {
      "[Content_Types].xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/></Types>`),
      "_rels/.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`),
      "xl/workbook.xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Chart" sheetId="1" r:id="rId1"/><sheet name="Filtered yields" sheetId="2" r:id="rId2"/><sheet name="Sources &amp; notes" sheetId="3" r:id="rId3"/></sheets></workbook>`),
      "xl/_rels/workbook.xml.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/></Relationships>`),
      "xl/worksheets/sheet1.xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews><sheetData/><drawing r:id="rId1"/></worksheet>`),
      "xl/worksheets/_rels/sheet1.xml.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/></Relationships>`),
      "xl/worksheets/sheet2.xml": strToU8(sheetXml(dataRows)),
      "xl/worksheets/sheet3.xml": strToU8(sheetXml(sourceRows)),
      "xl/drawings/drawing1.xml": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><xdr:twoCellAnchor><xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:to><xdr:col>18</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>27</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to><xdr:graphicFrame><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="Yield chart"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr><xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rId1"/></a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor></xdr:wsDr>`),
      "xl/drawings/_rels/drawing1.xml.rels": strToU8(`<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/chart" Target="../charts/chart1.xml"/></Relationships>`),
      "xl/charts/chart1.xml": strToU8(xlsxChartXml(chartSeries, lastRow, startDate, effectiveEnd, chartDomain.min, chartDomain.max)),
    };
    const archive = zipSync(files, { level: 6 });
    downloadBlob(new Blob([archive as BlobPart], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `government-bond-yields-${startDate}-${effectiveEnd}.xlsx`);
    setExportMessage(`${shownRows.length.toLocaleString()} observations exported with source notes.`);
  }

  return <div className="research-page">
    <section className="page-heading"><div><p className="eyebrow">SOVEREIGN RATES · DAILY SNAPSHOTS</p><h1>Government bond yields</h1><p>Compare each market’s published 10-year benchmark. Definitions differ by country; values stay in their source units without filling gaps.</p></div><div className="snapshot-stamp"><span className="pulse-dot"/> {snapshot ? `Version ${envelope?.version} · ${new Date(snapshot.retrievedAt).toLocaleDateString("en-GB", { dateStyle: "medium" })}` : loaded.status === "loading" ? "Loading snapshot" : "Waiting for first snapshot"}</div></section>
      <section className="data-boundary-note"><strong>Hosted purpose setting: personal interview · owner-only Site.</strong><span>This records intended use only; it does not establish reuse rights. Euronext and Banca d’Italia terms apply, written permission has not been verified, and Italy BMK0200 upstream vendors are not itemized. Local imports stay in this browser tab and are not uploaded or saved.</span></section>
    <section className="control-panel">
      <div className="filter-row"><label>From <input type="date" min={minDate} max={effectiveEnd || undefined} value={startDate} onChange={(event) => { setStartDate(event.target.value); setPeriodPreset(null); }} /></label><label>To <input type="date" min={startDate} max={maxDate || undefined} value={effectiveEnd} onChange={(event) => { setEndDate(event.target.value); setPeriodPreset(null); }} /></label><div className="range-buttons" aria-label="Quick date range">{([["1Y", "last-1-year"], ["3Y", "last-3-years"], ["5Y", "last-5-years"], ["YTD", "year-to-date"], ["MAX", "since-2020"]] as const).map(([label, key]) => <button key={label} aria-pressed={periodPreset === key} className={`quiet-button ${periodPreset === key ? "period-active" : ""}`} onClick={() => applyPeriod(key)}>{label}</button>)}</div></div>
      <div className="chart-options-row"><fieldset className="chart-option-set"><legend>Window definition</legend><div className="period-toggles"><button type="button" className={`quiet-button ${periodMode === "rolling" ? "period-active" : ""}`} aria-pressed={periodMode === "rolling"} disabled={!currentPreset || currentPreset.years === null} onClick={() => changePeriodMode("rolling")}>Rolling dates</button><button type="button" className={`quiet-button ${periodMode === "calendar" ? "period-active" : ""}`} aria-pressed={periodMode === "calendar"} disabled={!currentPreset || currentPreset.years === null} onClick={() => changePeriodMode("calendar")}>Calendar years</button></div></fieldset><fieldset className="chart-option-set"><legend>Date labels</legend><div className="period-toggles"><button type="button" className={`quiet-button ${dateGrid === "quarterly" ? "period-active" : ""}`} aria-pressed={dateGrid === "quarterly"} onClick={() => setDateGrid("quarterly")}>Quarterly</button><button type="button" className={`quiet-button ${dateGrid === "semiannual" ? "period-active" : ""}`} aria-pressed={dateGrid === "semiannual"} onClick={() => setDateGrid("semiannual")}>Semiannual</button></div></fieldset><span className="chart-range-summary">True bounds: {startDate} to {effectiveEnd || "latest"}</span></div>
      <div className="country-toggles" aria-label="Select countries">{BOND_COUNTRIES.map((country) => { const available = !!series[country.key]?.length; const checked = selected.includes(country.key); return <button key={country.key} onClick={() => available && toggle(country.key)} disabled={!available} aria-pressed={checked} className={`country-toggle ${checked ? "is-selected" : ""} ${available ? "" : "is-unavailable"}`}><i style={{ backgroundColor: country.color }} />{country.name}<span>{available ? localSeries[country.key] ? "Local import" : snapshot?.sourceStatus?.[country.key]?.status ?? "Hosted" : country.status === "hosted" ? "No snapshot" : "Local only"}</span></button>; })}</div>
      <div className="export-row"><label className="button button-secondary file-button"><Upload size={15}/> Import local CSV / JSON<input type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => void importFile(event.target.files?.[0])} /></label>{localLabel && <span className="local-file-indicator">In memory · {localLabel}<button onClick={() => { setLocalSeries({}); setLocalLabel(""); setSelected(["US", "UK", "France", "Italy", "Germany", "Japan"]); }}>Clear</button></span>}<span className="export-spacer"/><button className="button button-secondary" onClick={exportWorkbook} disabled={!shownRows.length || invalidRange}><FileSpreadsheet size={15}/> Excel with chart</button><button className="button button-secondary" onClick={() => void exportChart("svg")} disabled={!shownRows.length || invalidRange}><Download size={15}/> SVG</button><button className="button button-primary" onClick={() => void exportChart("png")} disabled={!shownRows.length || invalidRange}><ImageDown size={15}/> 3840 × 2160 PNG</button></div>
      {importError && <p className="inline-error" role="alert">{importError}</p>}{invalidRange && <p className="inline-error" role="alert">The end date must be on or after the start date.</p>}{exportMessage && <p className="inline-success" role="status">{exportMessage}</p>}
    </section>
    <section className="chart-panel"><div className="panel-heading"><div><p className="eyebrow">FILTERED DAILY SERIES · PERCENT PER ANNUM</p><h2>{shownRows.length ? `${shownRows.length.toLocaleString()} observations` : "No observations in this range"}</h2></div><span className="unit-pill">True bounds · {startDate} — {effectiveEnd || "latest"}</span></div>
      {shownRows.length && !invalidRange ? <div className="chart-scroll"><BondYieldChart chartRef={chartRef} series={filtered} selected={selected} startDate={startDate} endDate={effectiveEnd} dateGrid={dateGrid} periodLabel={currentPreset?.label ?? "Custom dates"} periodDescription={periodDescription} versionLabel={`snapshot v${envelope?.version ?? "unverified local import"}${localLabel ? ` · local import ${localLabel}` : ""}`} retrievedAt={snapshot?.retrievedAt ?? "local file retrieval not verified"} sources={Object.fromEntries(selected.map((country) => [country, localSeries[country] ? { agency: "Local file · source not verified", seriesId: localLabel } : snapshot?.sources?.[country] ?? BOND_SOURCE_DETAILS[country]]))}/></div> : <div className="empty-chart"><strong>{loaded.status === "error" ? "Snapshot could not be loaded" : "No observations in this range"}</strong><span>{loaded.message ?? "Once a permitted source snapshot is available, it will appear here. You can import a local six-country CSV for analysis in this browser."}</span></div>}
      <div className="chart-footer"><span><i className="legend-line"/> Published observations only</span><span>Missing dates are left blank · No interpolation or forward fill</span><span>{snapshot?.historyComplete ? "History complete" : "Imported data may contain a partial history"}</span></div>
    </section>
    <section className="source-grid">{BOND_COUNTRIES.map((country) => { const status = snapshot?.sourceStatus?.[country.key]; const count = series[country.key]?.length ?? 0; return <article className="source-card" key={country.key}><div className="source-card-top"><span className="country-mark" style={{ background: country.color }}/><strong>{country.name}</strong><span className={`source-status ${count ? status?.status === "stale" ? "stale" : "current" : "restricted"}`}>{count ? status?.status ?? "local import" : country.status === "hosted" ? "Awaiting snapshot" : "Local only"}</span></div><p>{country.definition}</p><dl><div><dt>Source</dt><dd>{country.agency}</dd></div><div><dt>Series</dt><dd>{BOND_SOURCE_DETAILS[country.key].seriesId}</dd></div><div><dt>Coverage</dt><dd>{count ? `${count.toLocaleString()} observations · ${series[country.key]?.[0]?.date} to ${series[country.key]?.at(-1)?.date}` : "Not loaded"}</dd></div></dl><a href={country.sourceUrl} target="_blank" rel="noreferrer">Source and reuse terms ↗</a><small>{country.rightsNote}</small></article>; })}</section>
  <p className="footnote">Series are published under different methods: par curves, fitted term structures, or benchmark indices. They are useful for comparison, but are not perfectly equivalent instruments.</p>
  </div>;
}

function parseCsvSeries(text: string): Partial<Record<CountryKey, YieldPoint[]>> {
  const [head, ...lines] = text.trim().split(/\r?\n/);
  if (!head) return {};
  const headers = parseCsvLine(head).map((value) => value.trim().toLowerCase());
  const dateIndex = headers.findIndex((header) => header === "date" || header === "observation_date");
  if (dateIndex < 0) throw new Error("CSV needs a Date column.");
  const indexes = BOND_COUNTRIES.map(({ key }) => ({ key, index: headers.findIndex((header) => header === key.toLowerCase() || header === `${key.toLowerCase()}_yield_pct` || header === `${key.toLowerCase()}_10y`) })).filter((entry) => entry.index >= 0);
  const result: Partial<Record<CountryKey, YieldPoint[]>> = {};
  const previousDate = new Map<CountryKey, string>();
  const seenDates = new Set<string>();
  let lastDate = "";
  for (const line of lines) {
    const cells = parseCsvLine(line); if (cells.every((cell) => !cell.trim())) continue;
    const date = cells[dateIndex]?.trim();
    if (!validIsoDate(date)) throw new Error(`CSV contains an invalid calendar date: ${date || "blank"}.`);
    if (seenDates.has(date)) throw new Error(`CSV contains a duplicate date: ${date}.`);
    if (lastDate && date <= lastDate) throw new Error("CSV dates must be strictly ascending.");
    seenDates.add(date);
    lastDate = date;
    for (const { key, index } of indexes) {
      const cell = cells[index]?.trim(); if (!cell) continue;
      const value = Number(cell);
      if (!Number.isFinite(value)) throw new Error(`CSV ${key} value for ${date} is not numeric.`);
      if (previousDate.has(key) && date <= previousDate.get(key)!) throw new Error(`CSV ${key} dates must be strictly ascending.`);
      result[key] ??= [];
      result[key]!.push({ date, value }); previousDate.set(key, date);
    }
  }
  if (!Object.keys(result).length) throw new Error("CSV did not contain recognized country yield columns.");
  return result;
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = []; let cell = ""; let quoted = false;
  for (let index = 0; index < line.length; index++) {
    const char = line[index];
    if (char === '"' && line[index + 1] === '"' && quoted) { cell += '"'; index++; }
    else if (char === '"') quoted = !quoted;
    else if (char === "," && !quoted) { cells.push(cell); cell = ""; }
    else cell += char;
  }
  cells.push(cell); return cells;
}

function parseJsonSeries(value: unknown): Partial<Record<CountryKey, YieldPoint[]>> {
  if (Array.isArray(value)) {
    if (!value.length) return {};
    const first = value[0];
    if (!first || typeof first !== "object") throw new Error("JSON rows must be objects.");
    const headers = Object.keys(first as Record<string, unknown>);
    const dates = value.map((row) => row as Record<string, unknown>);
    const quote = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const normalized = [headers.map(quote).join(","), ...dates.map((row) => headers.map((header) => quote(row[header])).join(","))].join("\n");
    return parseCsvSeries(normalized);
  }
  if (!value || typeof value !== "object") return {};
  const object = value as Record<string, unknown>; const raw = (object.series && typeof object.series === "object" ? object.series : object) as Record<string, unknown>;
  const result: Partial<Record<CountryKey, YieldPoint[]>> = {};
  for (const country of BOND_COUNTRIES) {
    const rows = raw[country.key] ?? raw[country.key.toLowerCase()];
    if (Array.isArray(rows)) {
      const countryRows: YieldPoint[] = [];
      let previousDate = "";
      for (const row of rows) {
        if (!row || typeof row !== "object") throw new Error(`JSON series ${country.key} contains an invalid row.`);
        const item = row as Record<string, unknown>; const date = String(item.date ?? ""); const value = item.value === null ? null : Number(item.value);
        if (!validIsoDate(date) || (value !== null && !Number.isFinite(value))) throw new Error(`JSON series ${country.key} has an invalid observation.`);
        if (date <= previousDate) throw new Error(`JSON series ${country.key} dates must be unique and strictly ascending.`);
        if (item.value !== null) countryRows.push({ date, value }); else countryRows.push({ date, value: null });
        previousDate = date;
      }
      if (countryRows.length) result[country.key] = countryRows;
    }
  }
  return result;
}

function sheetXml(rows: Array<Array<string | number>>) {
  const cell = (value: string | number, row: number, column: number) => {
    const address = `${columnName(column)}${row}`;
    if (value === "") return "";
    if (typeof value === "number") return `<c r="${address}"><v>${value}</v></c>`;
    const escaped = xmlEscape(value);
    return `<c r="${address}" t="inlineStr"><is><t xml:space="preserve">${escaped}</t></is></c>`;
  };
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${rows.map((row, index) => `<row r="${index + 1}">${row.map((value, column) => cell(value, index + 1, column + 1)).join("")}</row>`).join("")}</sheetData></worksheet>`;
}

function countryDash(country: CountryKey): "dot" | "dash" | "solid" {
  if (country === "US") return "dot";
  if (country === "France" || country === "Italy") return "dash";
  return "solid";
}

function xlsxSeries(index: number, country: CountryKey, color: string, dash: "dot" | "dash" | "solid") {
  return { index, country, color: color.replace("#", ""), dash, column: columnName(index + 2) };
}

function xlsxChartXml(series: Array<ReturnType<typeof xlsxSeries>>, lastRow: number, start: string, end: string, yMin: number, yMax: number) {
  const formulas = series.map(({ index, color, dash, column }) => `<c:ser><c:idx val="${index}"/><c:order val="${index}"/><c:tx><c:strRef><c:f>'Filtered yields'!$${column}$1</c:f></c:strRef></c:tx><c:spPr><a:ln w="28575" cap="flat"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill>${dash === "solid" ? "" : `<a:prstDash val="${dash}"/>`}</a:ln></c:spPr><c:marker><c:symbol val="none"/></c:marker><c:cat><c:strRef><c:f>'Filtered yields'!$A$2:$A$${lastRow}</c:f></c:strRef></c:cat><c:val><c:numRef><c:f>'Filtered yields'!$${column}$2:$${column}$${lastRow}</c:f></c:numRef></c:val></c:ser>`).join("");
  const title = `Government bond yields · ${start} to ${end}`;
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:lang val="en-GB"/><c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-GB" sz="1400" b="1"/><a:t>${xmlEscape(title)}</a:t></a:r><a:endParaRPr lang="en-GB"/></a:p></c:rich></c:tx><c:overlay val="0"/></c:title><c:plotArea><c:layout/><c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>${formulas}<c:axId val="10"/><c:axId val="20"/></c:lineChart><c:catAx><c:axId val="10"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:tickLblPos val="nextTo"/><c:crossAx val="20"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx><c:valAx><c:axId val="20"/><c:scaling><c:orientation val="minMax"/><c:min val="${yMin}"/><c:max val="${yMax}"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/><c:majorUnit val="1"/><c:numFmt formatCode="0\\%" sourceLinked="0"/><c:tickLblPos val="nextTo"/><c:crossAx val="10"/><c:crosses val="autoZero"/><c:crossBetween val="between"/><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-GB"/><a:t>Yield (%)</a:t></a:r><a:endParaRPr lang="en-GB"/></a:p></c:rich></c:tx></c:title></c:valAx></c:plotArea><c:legend><c:legendPos val="b"/><c:layout/><c:overlay val="0"/></c:legend><c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/><c:showDLblsOverMax val="0"/></c:chart><c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1000"/></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr></c:chartSpace>`;
}

function columnName(value: number) { let name = ""; while (value) { const remainder = (value - 1) % 26; name = String.fromCharCode(65 + remainder) + name; value = Math.floor((value - 1) / 26); } return name; }
function xmlEscape(value: string) { return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;"); }
function validIsoDate(value: string | undefined): value is string { if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false; const parsed = new Date(`${value}T00:00:00.000Z`); return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value; }
function downloadBlob(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url); }
