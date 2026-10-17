"use client";

import { useImperativeHandle, useMemo, useRef, useState, type Ref } from "react";
import { BOND_COUNTRIES, type CountryKey, type YieldPoint } from "@/app/data/catalog";
import { buildBondChartModel, exactYieldAtDate, nearestPublishedDate, type BondDateGrid } from "@/lib/bond-chart-logic";

type Props = {
  series: Partial<Record<CountryKey, YieldPoint[]>>;
  selected: CountryKey[];
  startDate: string;
  endDate: string;
  dateGrid: BondDateGrid;
  chartRef?: Ref<SVGSVGElement>;
  periodLabel: string;
  periodDescription: string;
  versionLabel: string;
  retrievedAt?: string;
  sources?: Partial<Record<CountryKey, { agency?: string; seriesId?: string }>>;
};

const LEFT = 88, RIGHT = 1168, TOP = 132, BOTTOM = 530;

export function BondYieldChart(props: Props) {
  const { series, selected, startDate, endDate, dateGrid } = props;
  const [hoverDate, setHoverDate] = useState<string | null>(null);
  const svgElement = useRef<SVGSVGElement | null>(null);
  const model = useMemo(() => buildBondChartModel(series, selected, startDate, endDate, dateGrid), [series, selected, startDate, endDate, dateGrid]);
  useImperativeHandle(props.chartRef, () => svgElement.current!, []);
  const hasData = model.dates.length > 0;
  const sourceNotes = selected.map((key) => {
    const country = BOND_COUNTRIES.find((item) => item.key === key)!;
    const source = props.sources?.[key];
    return `${country.name}: ${source?.agency ?? country.agency} · ${source?.seriesId ?? "series ID unavailable"}`;
  });
  const sourceLines = [sourceNotes.slice(0, 3), sourceNotes.slice(3)];
  const hoverX = hoverDate ? model.xForDate(hoverDate) : null;
  const tooltipWidth = 230;
  const tooltipHeight = 43 + selected.length * 20;
  const tooltipX = hoverX !== null && hoverX > (LEFT + RIGHT) / 2 ? Math.max(LEFT + 4, hoverX - tooltipWidth - 13) : Math.min(RIGHT - tooltipWidth - 4, (hoverX ?? LEFT) + 13);

  function chooseNearestAtClientX(clientX: number, clientY: number) {
    const svg = svgElement.current;
    const matrix = svg?.getScreenCTM();
    if (!svg || !matrix || !model.dates.length) return;
    const point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    const local = point.matrixTransform(matrix.inverse());
    if (local.x < LEFT || local.x > RIGHT) { setHoverDate(null); return; }
    const fraction = (local.x - LEFT) / (RIGHT - LEFT);
    const wantedMs = Date.parse(`${startDate}T00:00:00Z`) + fraction * (Date.parse(`${endDate}T00:00:00Z`) - Date.parse(`${startDate}T00:00:00Z`));
    const targetDate = new Date(wantedMs).toISOString().slice(0, 10);
    setHoverDate(nearestPublishedDate(model.dates, targetDate));
  }

  function moveKeyboard(direction: -1 | 1) {
    if (!model.dates.length) return;
    const current = hoverDate ? model.dates.indexOf(hoverDate) : direction > 0 ? -1 : model.dates.length;
    setHoverDate(model.dates[Math.max(0, Math.min(model.dates.length - 1, current + direction))]);
  }

  return <svg ref={svgElement} className="yield-chart" viewBox="0 0 1200 675" role="img" aria-label={`${props.periodLabel}; ${props.periodDescription}; ${startDate} through ${endDate}`} xmlns="http://www.w3.org/2000/svg" fontFamily="Arial, Helvetica, sans-serif">
    <rect x="0" y="0" width="1200" height="675" fill="#fff" />
    <text x="88" y="37" fontSize="23" fontWeight="700" fill="#223831">Government bond yields · 10-year benchmarks</text>
    <text x="88" y="62" fontSize="13" fill="#52665c">{props.periodLabel} · {props.periodDescription} · true range {startDate} to {endDate} · percent per annum</text>
    <text x="88" y="81" fontSize="11" fill="#77857d">10-year measures vary by source (par curves, fitted term structures or benchmark indices); they are not identical instruments.</text>
    {selected.map((country, index) => {
      const item = BOND_COUNTRIES.find((candidate) => candidate.key === country)!;
      const x = 88 + (index % 3) * 355;
      const y = 104 + Math.floor(index / 3) * 21;
      return <g key={`legend-${country}`}><line x1={x} x2={x + 25} y1={y} y2={y} stroke={item.color} strokeWidth="3" strokeDasharray={dashPattern(country)} /><text x={x + 33} y={y + 4} fontSize="12" fill="#33463d">{item.name}</text></g>;
    })}
    {model.ticks.map((tick) => <g key={tick.value}><line x1={LEFT} x2={RIGHT} y1={tick.y} y2={tick.y} stroke="#dce5df" strokeDasharray="5 7"/><text x={LEFT - 12} y={tick.y + 4} textAnchor="end" fontSize="12" fill="#738078">{tick.label}</text></g>)}
    {model.verticalGuides.map((guide) => <line key={`grid-${guide.date}`} x1={guide.x} x2={guide.x} y1={TOP} y2={BOTTOM} stroke="#e9eeeb" strokeDasharray="3 6" strokeWidth="1"/>)}
    <line x1={LEFT} x2={RIGHT} y1={BOTTOM} y2={BOTTOM} stroke="#aeb9b2" strokeWidth="1.5"/>
    {model.labels.map((label) => <g key={label.date}><line x1={label.x} x2={label.x} y1={BOTTOM} y2={BOTTOM + 7} stroke="#aebbb4"/><text x={label.x} y={BOTTOM + 25} textAnchor={label.anchor} fontSize="11" fill="#738078">{label.text}</text></g>)}
    {selected.map((country) => {
      const item = BOND_COUNTRIES.find((candidate) => candidate.key === country)!;
      const last = model.lastPoints[country];
      return <g key={`curve-${country}`}><path d={model.paths[country] ?? ""} fill="none" stroke={item.color} strokeWidth="2.5" strokeDasharray={dashPattern(country)} strokeLinejoin="round" strokeLinecap="round"/>{last && <circle cx={last.x} cy={last.y} r="3.5" fill={item.color}/>}</g>;
    })}
    <text x="21" y="340" transform="rotate(-90 21 340)" fontSize="12" fill="#62736b">Yield (%)</text>
    {sourceLines.map((line, index) => line.length ? <text key={`source-${index}`} x="88" y={596 + index * 17} fontSize="9.5" fill="#586a61">Sources: {line.join(" · ")}</text> : null)}
    <text x="88" y="636" fontSize="9.5" fill="#586a61">Retrieved {props.retrievedAt ?? "from selected local data"} · {props.versionLabel} · {props.periodDescription}</text>
    <text x="88" y="653" fontSize="9.5" fill="#738078">Published observations only · missing values are not filled or interpolated · no data is shown where an exact daily observation is absent.</text>
    {hasData && <rect className="chart-hit-area" x={LEFT} y={TOP} width={RIGHT - LEFT} height={BOTTOM - TOP} fill="transparent" stroke="transparent" pointerEvents="all" tabIndex={0} role="slider" aria-label="Chart crosshair. Use left and right arrow keys to select the nearest published date." aria-valuemin={0} aria-valuemax={model.dates.length - 1} aria-valuenow={hoverDate ? Math.max(0, model.dates.indexOf(hoverDate)) : 0} aria-valuetext={hoverDate ? `Nearest published observation date ${hoverDate}` : "No date selected"} onPointerMove={(event) => chooseNearestAtClientX(event.clientX, event.clientY)} onPointerLeave={() => setHoverDate(null)} onFocus={() => { if (!hoverDate) setHoverDate(model.dates[Math.floor(model.dates.length / 2)] ?? null); }} onKeyDown={(event) => { if (event.key === "ArrowLeft") { event.preventDefault(); moveKeyboard(-1); } else if (event.key === "ArrowRight") { event.preventDefault(); moveKeyboard(1); } else if (event.key === "Escape") setHoverDate(null); }}/>}
    {hoverDate && hoverX !== null && <g className="interactive-chart-overlay" pointerEvents="none" role="status" aria-live="polite">
      <line x1={hoverX} x2={hoverX} y1={TOP} y2={BOTTOM} stroke="#53695d" strokeDasharray="4 4" strokeWidth="1.5"/>
      {selected.map((country) => {
        const value = exactYieldAtDate(series[country], hoverDate);
        const item = BOND_COUNTRIES.find((candidate) => candidate.key === country)!;
        return value === null ? null : <circle key={`hover-dot-${country}`} cx={hoverX} cy={model.yForValue(value)} r="5" fill={item.color} stroke="#fff" strokeWidth="2"/>;
      })}
      <rect x={tooltipX} y="139" width={tooltipWidth} height={tooltipHeight} rx="7" fill="#fff" stroke="#cdd8d0" strokeWidth="1.2" opacity="0.97"/>
      <text x={tooltipX + 10} y="158" fontSize="11" fontWeight="700" fill="#31483b">Nearest published date · {hoverDate}</text>
      {selected.map((country, index) => {
        const item = BOND_COUNTRIES.find((candidate) => candidate.key === country)!;
        const value = exactYieldAtDate(series[country], hoverDate);
        return <g key={`tooltip-${country}`}><circle cx={tooltipX + 14} cy={174 + index * 19} r="3.5" fill={item.color}/><text x={tooltipX + 25} y={178 + index * 19} fontSize="11" fill="#43584c">{item.name}</text><text x={tooltipX + tooltipWidth - 10} y={178 + index * 19} textAnchor="end" fontSize="11" fontWeight="600" fill="#253b30">{value === null ? "No data" : `${String(value)}%`}</text></g>;
      })}
    </g>}
  </svg>;
}

export async function exportBondChart(svg: SVGSVGElement, format: "svg" | "png", filename: string) {
  const copy = svg.cloneNode(true) as SVGSVGElement;
  copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  copy.setAttribute("width", "3840");
  copy.setAttribute("height", "2160");
  copy.querySelectorAll(".interactive-chart-overlay, .chart-hit-area").forEach((node) => node.remove());
  const source = new XMLSerializer().serializeToString(copy);
  if (format === "svg") {
    downloadBlob(new Blob([source], { type: "image/svg+xml;charset=utf-8" }), `${filename}.svg`);
    return;
  }
  const image = new Image();
  const url = URL.createObjectURL(new Blob([source], { type: "image/svg+xml;charset=utf-8" }));
  try {
    await new Promise<void>((resolve, reject) => { image.onload = () => resolve(); image.onerror = () => reject(new Error("Chart image could not be rendered.")); image.src = url; });
    const canvas = document.createElement("canvas"); canvas.width = 3840; canvas.height = 2160;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("High-resolution image export is unavailable in this browser.");
    context.fillStyle = "#fff"; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((value) => value ? resolve(value) : reject(new Error("Could not encode PNG.")), "image/png"));
    downloadBlob(blob, `${filename}-3840px.png`);
  } finally { URL.revokeObjectURL(url); }
}

function dashPattern(country: CountryKey) {
  return country === "US" ? "2 6" : country === "France" || country === "Italy" ? "7 5" : undefined;
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
