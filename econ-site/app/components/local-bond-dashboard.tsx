"use client";

import { Download, FileSpreadsheet, ImageDown, Upload } from "lucide-react";
import { strToU8, zipSync } from "fflate";
import { useMemo, useRef, useState } from "react";
import { useSnapshot } from "@/app/components/snapshot-fetch";
import { BOND_COUNTRIES, BOND_SOURCE_DETAILS, type BondSnapshot, type CountryKey, type YieldPoint } from "@/app/data/catalog";

type RawEnvelope = { snapshot: BondSnapshot; version: number; manifest: Record<string, unknown> };
type XY = { x: number; y: number; date: string; value: number };
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
  const values = selected.flatMap((country) => (filtered[country] ?? []).flatMap((point) => point.value === null ? [] : [point.value]));
  const low = values.length ? Math.min(...values) : -1;
  const high = values.length ? Math.max(...values) : 1;
  const pad = Math.max((high - low) * 0.1, 0.15);
  const yMin = Math.floor((low - pad) * 4) / 4;
  const yMax = Math.ceil((high + pad) * 4) / 4;
  const chart = buildChart(filtered, selected, startDate, effectiveEnd, yMin, yMax);
  const shownRows = selected.flatMap((country) => (filtered[country] ?? []).flatMap((point) => point.value === null ? [] : [{ date: point.date, country, value: point.value }]));
  const sourceNotes = selected.map((country) => localSeries[country]
    ? `${country}: local file ${localLabel} (source and completeness not verified by the Site)`
    : `${country}: ${BOND_SOURCE_DETAILS[country].agency}; ${snapshot?.sourceStatus?.[country]?.status ?? "not loaded"}`);

  async function importFile(file?: File) {
    if (!file) return;
    setImportError("");
    try {
      const text = await file.text();
      const parsed = file.name.toLowerCase().endsWith(".json") ? parseJsonSeries(JSON.parse(text)) : parseCsvSeries(text);
      if (!Object.keys(parsed).length) throw new Error("No recognized country/date/yield columns were found.");
      setLocalSeries(parsed);
      setLocalLabel(file.name);
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
    const svg = chartRef.current.cloneNode(true) as SVGSVGElement;
    svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    svg.setAttribute("width", "3840");
    svg.setAttribute("height", "2160");
    svg.setAttribute("viewBox", "0 0 1200 675");
    const source = new XMLSerializer().serializeToString(svg);
    if (format === "svg") downloadBlob(new Blob([source], { type: "image/svg+xml;charset=utf-8" }), `government-bond-yields-${startDate}-${effectiveEnd}.svg`);
    else {
      const image = new Image();
      const url = URL.createObjectURL(new Blob([source], { type: "image/svg+xml;charset=utf-8" }));
      try {
        await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error("Chart image could not be rendered.")); image.src = url; });
        const canvas = document.createElement("canvas"); canvas.width = 3840; canvas.height = 2160;
        const context = canvas.getContext("2d");
        if (!context) throw new Error("High-resolution image export is unavailable in this browser.");
        context.fillStyle = "#ffffff"; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(image, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((value) => value ? resolve(value) : reject(new Error("Could not encode PNG.")), "image/png"));
        downloadBlob(blob, `government-bond-yields-${startDate}-${effectiveEnd}-3840px.png`);
      } finally { URL.revokeObjectURL(url); }
    }
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
      "xl/charts/chart1.xml": strToU8(xlsxChartXml(chartSeries, lastRow, startDate, effectiveEnd)),
    };
    const archive = zipSync(files, { level: 6 });
    downloadBlob(new Blob([archive as BlobPart], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), `government-bond-yields-${startDate}-${effectiveEnd}.xlsx`);
    setExportMessage(`${shownRows.length.toLocaleString()} observations exported with source notes.`);
  }

  return <div className="research-page">
    <section className="page-heading"><div><p className="eyebrow">SOVEREIGN RATES · DAILY SNAPSHOTS</p><h1>Government bond yields</h1><p>Compare each market’s published 10-year benchmark. Definitions differ by country; values stay in their source units without filling gaps.</p></div><div className="snapshot-stamp"><span className="pulse-dot"/> {snapshot ? `Version ${envelope?.version} · ${new Date(snapshot.retrievedAt).toLocaleDateString("en-GB", { dateStyle: "medium" })}` : loaded.status === "loading" ? "Loading snapshot" : "Waiting for first snapshot"}</div></section>
      <section className="data-boundary-note"><strong>Hosted purpose setting: personal interview · owner-only Site.</strong><span>This records intended use only; it does not establish reuse rights. Euronext and Banca d’Italia terms apply, written permission has not been verified, and Italy BMK0200 upstream vendors are not itemized. Local imports stay in this browser tab and are not uploaded or saved.</span></section>
    <section className="control-panel">
      <div className="filter-row"><label>From <input type="date" min={minDate} max={effectiveEnd || undefined} value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>To <input type="date" min={startDate} max={maxDate || undefined} value={effectiveEnd} onChange={(event) => setEndDate(event.target.value)} /></label><div className="range-buttons" aria-label="Quick date range">{[["1Y", 1], ["3Y", 3], ["5Y", 5], ["MAX", 100]].map(([label, years]) => <button key={label} className="quiet-button" onClick={() => { if (!maxDate) return; setStartDate(years === 100 ? minDate : `${Number(maxDate.slice(0, 4)) - Number(years) + 1}${maxDate.slice(4)}`); setEndDate(maxDate); }}>{label}</button>)}</div></div>
      <div className="country-toggles" aria-label="Select countries">{BOND_COUNTRIES.map((country) => { const available = !!series[country.key]?.length; const checked = selected.includes(country.key); return <button key={country.key} onClick={() => available && toggle(country.key)} disabled={!available} aria-pressed={checked} className={`country-toggle ${checked ? "is-selected" : ""} ${available ? "" : "is-unavailable"}`}><i style={{ backgroundColor: country.color }} />{country.name}<span>{available ? localSeries[country.key] ? "Local import" : snapshot?.sourceStatus?.[country.key]?.status ?? "Hosted" : country.status === "hosted" ? "No snapshot" : "Local only"}</span></button>; })}</div>
      <div className="export-row"><label className="button button-secondary file-button"><Upload size={15}/> Import local CSV / JSON<input type="file" accept=".csv,.json,text/csv,application/json" onChange={(event) => void importFile(event.target.files?.[0])} /></label>{localLabel && <span className="local-file-indicator">In memory · {localLabel}<button onClick={() => { setLocalSeries({}); setLocalLabel(""); setSelected(["US", "UK", "France", "Italy", "Germany", "Japan"]); }}>Clear</button></span>}<span className="export-spacer"/><button className="button button-secondary" onClick={exportWorkbook} disabled={!shownRows.length || invalidRange}><FileSpreadsheet size={15}/> Excel with chart</button><button className="button button-secondary" onClick={() => void exportChart("svg")} disabled={!shownRows.length || invalidRange}><Download size={15}/> SVG</button><button className="button button-primary" onClick={() => void exportChart("png")} disabled={!shownRows.length || invalidRange}><ImageDown size={15}/> 3840 × 2160 PNG</button></div>
      {importError && <p className="inline-error" role="alert">{importError}</p>}{invalidRange && <p className="inline-error" role="alert">The end date must be on or after the start date.</p>}{exportMessage && <p className="inline-success" role="status">{exportMessage}</p>}
    </section>
    <section className="chart-panel"><div className="panel-heading"><div><p className="eyebrow">FILTERED SERIES · PERCENT PER ANNUM</p><h2>{shownRows.length ? `${shownRows.length.toLocaleString()} observations` : "No observations in this range"}</h2></div><span className="unit-pill">{startDate} — {effectiveEnd || "latest"}</span></div>
      {shownRows.length && !invalidRange ? <div className="chart-scroll"><svg ref={chartRef} className="yield-chart" viewBox="0 0 1200 675" role="img" aria-label={`Selected sovereign bond yields from ${startDate} through ${effectiveEnd}`} xmlns="http://www.w3.org/2000/svg" fontFamily="Arial, Helvetica, sans-serif">
        <rect x="0" y="0" width="1200" height="675" fill="#fff" />
        <text x="72" y="40" fontSize="23" fontWeight="700" fill="#223831">Government bond yields · 10-year benchmarks</text><text x="72" y="64" fontSize="13" fill="#6b7c74">{startDate} to {effectiveEnd} · percent per annum · snapshot v{envelope?.version ?? "local import"}</text>
        {selected.map((country, index) => <g key={`legend-${country}`}><line x1={72 + index * 175} x2={96 + index * 175} y1="92" y2="92" stroke={COLORS[country]} strokeWidth="3" strokeDasharray={countryDash(country) === "dot" ? "1 5" : countryDash(country) === "dash" ? "6 4" : undefined}/><text x={104 + index * 175} y="96" fontSize="12" fill="#33463d">{country}</text></g>)}
        {chart.ticks.map((tick) => <g key={tick.value}><line x1="72" x2="1172" y1={tick.y} y2={tick.y} stroke="#e8edea"/><text x="58" y={tick.y + 4} textAnchor="end" fontSize="12" fill="#7c8b84">{tick.value.toFixed(1)}%</text></g>)}
        <line x1="72" x2="1172" y1="540" y2="540" stroke="#cbd4cf"/>
        {chart.labels.map((label) => <g key={label.date}><line x1={label.x} x2={label.x} y1="540" y2="546" stroke="#aebbb4"/><text x={label.x} y="566" textAnchor={label.anchor} fontSize="12" fill="#7c8b84">{label.text}</text></g>)}
        {selected.map((country) => <g key={country}><path d={chart.paths[country] ?? ""} fill="none" stroke={COLORS[country]} strokeWidth="2.3" strokeDasharray={countryDash(country) === "dot" ? "1 5" : countryDash(country) === "dash" ? "6 4" : undefined} strokeLinejoin="round" strokeLinecap="round" />{chart.lastPoints[country] && <circle cx={chart.lastPoints[country]!.x} cy={chart.lastPoints[country]!.y} r="4" fill={COLORS[country]}><title>{country} · {chart.lastPoints[country]!.date}: {chart.lastPoints[country]!.value.toFixed(3)}%</title></circle>}</g>)}
        <text x="18" y="300" transform="rotate(-90 18 300)" fontSize="12" fill="#62736b">Yield (%)</text>
        <text x="72" y="612" fontSize="10" fill="#586a61">Sources: {sourceNotes.join("  ·  ")}</text><text x="72" y="635" fontSize="10" fill="#586a61">Retrieved {snapshot?.retrievedAt ?? `from local file ${localLabel || "not imported"}`} · version {envelope?.version ?? "unverified local import"}</text><text x="72" y="655" fontSize="10" fill="#85938d">Missing observations remain blank · imported-file provenance and completeness were not verified.</text>
      </svg></div> : <div className="empty-chart"><strong>{loaded.status === "error" ? "Snapshot could not be loaded" : "No published bond snapshot yet"}</strong><span>{loaded.message ?? "Once a permitted source snapshot is available, it will appear here. You can import a local six-country CSV for analysis in this browser."}</span></div>}
      <div className="chart-footer"><span><i className="legend-line"/> Published observations only</span><span>Missing dates are left blank · No interpolation or forward fill</span><span>{snapshot?.historyComplete ? "History complete" : "Imported data may contain a partial history"}</span></div>
    </section>
    <section className="source-grid">{BOND_COUNTRIES.map((country) => { const status = snapshot?.sourceStatus?.[country.key]; const count = series[country.key]?.length ?? 0; return <article className="source-card" key={country.key}><div className="source-card-top"><span className="country-mark" style={{ background: country.color }}/><strong>{country.name}</strong><span className={`source-status ${count ? status?.status === "stale" ? "stale" : "current" : "restricted"}`}>{count ? status?.status ?? "local import" : country.status === "hosted" ? "Awaiting snapshot" : "Local only"}</span></div><p>{country.definition}</p><dl><div><dt>Source</dt><dd>{country.agency}</dd></div><div><dt>Series</dt><dd>{BOND_SOURCE_DETAILS[country.key].seriesId}</dd></div><div><dt>Coverage</dt><dd>{count ? `${count.toLocaleString()} observations · ${series[country.key]?.[0]?.date} to ${series[country.key]?.at(-1)?.date}` : "Not loaded"}</dd></div></dl><a href={country.sourceUrl} target="_blank" rel="noreferrer">Source and reuse terms ↗</a><small>{country.rightsNote}</small></article>; })}</section>
  <p className="footnote">Series are published under different methods: par curves, fitted term structures, or benchmark indices. They are useful for comparison, but are not perfectly equivalent instruments.</p>
  </div>;
}

function buildChart(series: Partial<Record<CountryKey, YieldPoint[]>>, selected: CountryKey[], start: string, end: string, yMin: number, yMax: number) {
  const left = 72; const right = 1172; const top = 124; const bottom = 540;
  const startTime = Date.parse(`${start}T00:00:00Z`); const endTime = Date.parse(`${end || start}T00:00:00Z`);
  const x = (date: string) => left + ((Date.parse(`${date}T00:00:00Z`) - startTime) / Math.max(endTime - startTime, 1)) * (right - left);
  const y = (value: number) => bottom - ((value - yMin) / Math.max(yMax - yMin, 1e-9)) * (bottom - top);
  const paths = {} as Record<CountryKey, string>; const lastPoints = {} as Partial<Record<CountryKey, XY>>;
  for (const country of selected) {
    const points = (series[country] ?? []).filter((point) => point.value !== null && point.date >= start && point.date <= end).map((point) => ({ x: x(point.date), y: y(point.value as number), date: point.date, value: point.value as number }));
    paths[country] = points.map((point, index) => `${index ? "L" : "M"}${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
    if (points.length) lastPoints[country] = points.at(-1);
  }
  const span = yMax - yMin; const tickStep = span > 10 ? 2 : span > 5 ? 1 : span > 2 ? 0.5 : 0.25;
  const firstTick = Math.ceil(yMin / tickStep) * tickStep;
  const ticks = []; for (let value = firstTick; value <= yMax + 0.0001; value += tickStep) ticks.push({ value, y: y(value) });
  const startYear = Number(start.slice(0, 4)); const endYear = Number((end || start).slice(0, 4));
  const step = Math.max(1, Math.ceil((endYear - startYear) / 5));
  const labelYears = Array.from({ length: Math.floor((endYear - startYear) / step) + 1 }, (_, index) => startYear + index * step);
  if (!labelYears.includes(endYear)) labelYears.push(endYear);
  const labels = labelYears.map((year, index) => ({ date: `${year}-01-01`, x: Math.max(left, Math.min(right, x(`${year}-01-01`))), text: String(year), anchor: index === 0 ? "start" as const : index === labelYears.length - 1 ? "end" as const : "middle" as const }));
  return { paths, lastPoints, ticks, labels };
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

function xlsxChartXml(series: Array<ReturnType<typeof xlsxSeries>>, lastRow: number, start: string, end: string) {
  const formulas = series.map(({ index, color, dash, column }) => `<c:ser><c:idx val="${index}"/><c:order val="${index}"/><c:tx><c:strRef><c:f>'Filtered yields'!$${column}$1</c:f></c:strRef></c:tx><c:spPr><a:ln w="28575" cap="flat"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill>${dash === "solid" ? "" : `<a:prstDash val="${dash}"/>`}</a:ln></c:spPr><c:marker><c:symbol val="none"/></c:marker><c:cat><c:strRef><c:f>'Filtered yields'!$A$2:$A$${lastRow}</c:f></c:strRef></c:cat><c:val><c:numRef><c:f>'Filtered yields'!$${column}$2:$${column}$${lastRow}</c:f></c:numRef></c:val></c:ser>`).join("");
  const title = `Government bond yields · ${start} to ${end}`;
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:lang val="en-GB"/><c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-GB" sz="1400" b="1"/><a:t>${xmlEscape(title)}</a:t></a:r><a:endParaRPr lang="en-GB"/></a:p></c:rich></c:tx><c:overlay val="0"/></c:title><c:plotArea><c:layout/><c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>${formulas}<c:axId val="10"/><c:axId val="20"/></c:lineChart><c:catAx><c:axId val="10"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="b"/><c:tickLblPos val="nextTo"/><c:crossAx val="20"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx><c:valAx><c:axId val="20"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="l"/><c:majorGridlines/><c:numFmt formatCode="0.0\%" sourceLinked="0"/><c:tickLblPos val="nextTo"/><c:crossAx val="10"/><c:crosses val="autoZero"/><c:crossBetween val="between"/><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-GB"/><a:t>Yield (%)</a:t></a:r><a:endParaRPr lang="en-GB"/></a:p></c:rich></c:tx></c:title></c:valAx></c:plotArea><c:legend><c:legendPos val="b"/><c:layout/><c:overlay val="0"/></c:legend><c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/><c:showDLblsOverMax val="0"/></c:chart><c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1000"/></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr></c:chartSpace>`;
}

function columnName(value: number) { let name = ""; while (value) { const remainder = (value - 1) % 26; name = String.fromCharCode(65 + remainder) + name; value = Math.floor((value - 1) / 26); } return name; }
function xmlEscape(value: string) { return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;"); }
function validIsoDate(value: string | undefined): value is string { if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false; const parsed = new Date(`${value}T00:00:00.000Z`); return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value; }
function downloadBlob(blob: Blob, name: string) { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url); }
