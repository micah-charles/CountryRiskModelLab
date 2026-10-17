import type { CountryKey, YieldPoint } from "../app/data/catalog.ts";

export const BOND_CHART_PRESETS = [
  { key: "last-3-years", label: "Last 3 years", years: 3 },
  { key: "last-1-year", label: "Last 1 year", years: 1 },
  { key: "year-to-date", label: "Year to date", years: null },
  { key: "last-5-years", label: "Last 5 years", years: 5 },
  { key: "since-2020", label: "2020–present", years: null },
] as const;
export type BondChartPresetKey = (typeof BOND_CHART_PRESETS)[number]["key"];

export type BondPeriodMode = "rolling" | "calendar";
export type BondDateGrid = "quarterly" | "semiannual";
export type BondPeriodBounds = { startDate: string; endDate: string; mode: BondPeriodMode | "fixed" };
export type BondChartModel = {
  yMin: number;
  yMax: number;
  ticks: Array<{ value: number; y: number; label: string }>;
  verticalGuides: Array<{ date: string; x: number }>;
  labels: Array<{ date: string; x: number; text: string; anchor: "start" | "middle" | "end" }>;
  paths: Partial<Record<CountryKey, string>>;
  lastPoints: Partial<Record<CountryKey, { x: number; y: number; date: string; value: number }>>;
  dates: string[];
  xForDate: (date: string) => number;
  yForValue: (value: number) => number;
};

export function resolveBondPeriodBounds(period: BondChartPresetKey, mode: BondPeriodMode, endDate: string): BondPeriodBounds {
  const preset = BOND_CHART_PRESETS.find((item) => item.key === period);
  if (!preset) throw new Error("Unknown bond chart period.");
  if (period === "since-2020") return { startDate: "2020-01-01", endDate, mode: "fixed" };
  if (period === "year-to-date") return { startDate: `${endDate.slice(0, 4)}-01-01`, endDate, mode: "fixed" };
  const startDate = mode === "calendar"
    ? `${Number(endDate.slice(0, 4)) - (preset.years ?? 1) + 1}-01-01`
    : shiftIsoYearClamped(endDate, -(preset.years ?? 1));
  return { startDate, endDate, mode };
}

export function shiftIsoYearClamped(date: string, amount: number): string {
  const [year, month, day] = date.split("-").map(Number);
  if (!year || !month || !day || !Number.isInteger(amount)) throw new Error("Expected an ISO calendar date and integer year offset.");
  const shiftedYear = year + amount;
  const lastDay = new Date(Date.UTC(shiftedYear, month, 0)).getUTCDate();
  return `${shiftedYear}-${String(month).padStart(2, "0")}-${String(Math.min(day, lastDay)).padStart(2, "0")}`;
}

export function calendarDateTicks(startDate: string, endDate: string, grid: BondDateGrid): string[] {
  const firstMonth = grid === "quarterly" ? 0 : 0;
  const monthStep = grid === "quarterly" ? 3 : 6;
  const start = Date.parse(`${startDate}T00:00:00Z`);
  const end = Date.parse(`${endDate}T00:00:00Z`);
  if (!Number.isFinite(start) || !Number.isFinite(end) || start > end) return [];
  const result: string[] = [];
  const startYear = Number(startDate.slice(0, 4));
  const endYear = Number(endDate.slice(0, 4));
  for (let year = startYear; year <= endYear; year++) {
    for (let month = firstMonth; month < 12; month += monthStep) {
      const tick = `${year}-${String(month + 1).padStart(2, "0")}-01`;
      const time = Date.parse(`${tick}T00:00:00Z`);
      if (time >= start && time <= end) result.push(tick);
    }
  }
  return result;
}

export function formatYieldTick(value: number): string {
  return `${Number.isInteger(value) ? String(value) : String(Number(value.toFixed(6)))}%`;
}

export function integerYieldDomain(values: number[]) {
  if (!values.length) return { min: -1, max: 1, ticks: [-1, 0, 1] };
  const low = Math.min(...values);
  const high = Math.max(...values);
  let min = Math.min(0, Math.floor(low - 0.1));
  let max = Math.max(0, Math.ceil(high + 0.1));
  if (min >= max) { min -= 1; max += 1; }
  const ticks = Array.from({ length: max - min + 1 }, (_, index) => min + index);
  return { min, max, ticks };
}

export function nearestPublishedDate(dates: string[], targetDate: string): string | null {
  if (!dates.length) return null;
  const target = Date.parse(`${targetDate}T00:00:00Z`);
  let low = 0, high = dates.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (dates[mid] < targetDate) low = mid + 1;
    else high = mid;
  }
  if (low === 0) return dates[0];
  if (low === dates.length) return dates.at(-1)!;
  const before = dates[low - 1], after = dates[low];
  return target - Date.parse(`${before}T00:00:00Z`) <= Date.parse(`${after}T00:00:00Z`) - target ? before : after;
}

/** Exact-date lookup only. Missing rows and explicit nulls both remain no data. */
export function exactYieldAtDate(rows: YieldPoint[] | undefined, date: string): number | null {
  if (!rows) return null;
  let low = 0, high = rows.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (rows[mid].date < date) low = mid + 1;
    else high = mid;
  }
  return rows[low]?.date === date && typeof rows[low].value === "number" && Number.isFinite(rows[low].value)
    ? rows[low].value
    : null;
}

export function buildBondChartModel(
  series: Partial<Record<CountryKey, YieldPoint[]>>,
  selected: CountryKey[],
  startDate: string,
  endDate: string,
  dateGrid: BondDateGrid,
): BondChartModel {
  const left = 88, right = 1168, top = 132, bottom = 530;
  const startTime = Date.parse(`${startDate}T00:00:00Z`);
  const endTime = Date.parse(`${endDate}T00:00:00Z`);
  const span = Math.max(endTime - startTime, 1);
  const xForDate = (date: string) => left + ((Date.parse(`${date}T00:00:00Z`) - startTime) / span) * (right - left);
  const values = selected.flatMap((country) => (series[country] ?? [])
    .filter((point) => point.date >= startDate && point.date <= endDate && point.value !== null)
    .map((point) => point.value as number));
  const domain = integerYieldDomain(values);
  const yForValue = (value: number) => bottom - ((value - domain.min) / (domain.max - domain.min)) * (bottom - top);
  const paths: Partial<Record<CountryKey, string>> = {};
  const lastPoints: Partial<Record<CountryKey, { x: number; y: number; date: string; value: number }>> = {};
  const hoverDates = new Set<string>();
  for (const country of selected) {
    const rows = (series[country] ?? []).filter((point) => point.date >= startDate && point.date <= endDate);
    const commands: string[] = [];
    let penDown = false;
    for (const point of rows) {
      if (point.value === null) { penDown = false; continue; }
      const px = xForDate(point.date), py = yForValue(point.value);
      commands.push(`${penDown ? "L" : "M"}${px.toFixed(2)},${py.toFixed(2)}`);
      penDown = true;
      hoverDates.add(point.date);
      lastPoints[country] = { x: px, y: py, date: point.date, value: point.value };
    }
    paths[country] = commands.join(" ");
  }
  const rawTicks = domain.ticks;
  const verticalGuides = calendarDateTicks(startDate, endDate, dateGrid).map((date) => ({ date, x: xForDate(date) }));
  const labels = verticalGuides.map(({ date, x }, index, all) => ({
    date,
    x,
    text: new Date(`${date}T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "2-digit", timeZone: "UTC" }),
    anchor: index === 0 ? "start" as const : index === all.length - 1 ? "end" as const : "middle" as const,
  }));
  return {
    yMin: domain.min,
    yMax: domain.max,
    ticks: rawTicks.map((value) => ({ value, y: yForValue(value), label: formatYieldTick(value) })),
    verticalGuides,
    labels,
    paths,
    lastPoints,
    dates: [...hoverDates].sort(),
    xForDate,
    yForValue,
  };
}
