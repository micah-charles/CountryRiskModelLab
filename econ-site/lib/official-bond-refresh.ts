/** Official-source downloads for the private Site's scheduled snapshot writer.
 * Numeric observations are parsed from agency exports, never estimated.
 */
export type Observation = { date: string; value: number };
export type RawDownload = { name: string; url: string; bytes: Uint8Array };
export type CountryDownload = { rows: Observation[]; raw: RawDownload[] };
export const CLOUD_COUNTRIES = ["US", "UK", "Germany", "Japan"] as const;
export const ALL_BOND_COUNTRIES = ["US", "UK", "France", "Italy", "Germany", "Japan"] as const;
export type OfficialCountry = typeof ALL_BOND_COUNTRIES[number];
const MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024;
const AGENCY_HOSTS = new Set(["home.treasury.gov", "www.bankofengland.co.uk", "webstat.banque-france.fr", "a2a.bancaditalia.it", "api.statistiken.bundesbank.de", "www.mof.go.jp"]);

export const OFFICIAL_SOURCES = {
  US: { agency: "U.S. Department of the Treasury", series_id: "Daily Treasury Par Yield Curve Rates: 10 Yr", definition: "10-year constant-maturity par yield from Treasury's daily estimated par curve; indicative bid-side quotes collected by the Federal Reserve Bank of New York.", source_url: "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", unit: "Percent per annum", frequency: "Daily", reuse: "Official Treasury-produced numeric series. Retain attribution and methodology; no series-specific redistribution restriction located. Government works and factual observations are distinguished from third-party licensed content." },
  UK: { agency: "Bank of England", series_id: "IUDMNPY", definition: "10-year nominal par yield from the fitted gilt curve, using the Variable Roughness Penalty model.", source_url: "https://www.bankofengland.co.uk/statistics/yield-curves", unit: "Percent per annum", frequency: "Daily", reuse: "UK Open Government Licence for Bank of England Database statistics, subject to stated exclusions. Attribute the Bank of England." },
  France: { agency: "Banque de France Webstat / Euronext", series_id: "FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA", definition: "TEC10 constant-maturity index for a notional 10-year OAT; calculated by Euronext from MTS France data.", source_url: "https://webstat.banque-france.fr/en/catalog/fm/FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA", unit: "Percent per annum", frequency: "Daily", reuse: "The Banque de France Webstat series is Euronext/MTS France-derived; Euronext terms apply and restrict redistribution. No written permission for this owner-only chart has been verified. The operator-selected personal-interview purpose records intended use only and does not establish reuse rights." },
  Italy: { agency: "Banca d'Italia", series_id: "MFN_BMK.D.020.922.0.EUR.210", definition: "Daily gross yield to maturity on the 10-year benchmark BTP, BMK0200. Metadata BIVA means Bank of Italy processing on various sources; upstream vendor list is not itemized. Daily observations are released through monthly financial-market statistics.", source_url: "https://www.bancaditalia.it/statistiche/tematiche/moneta-intermediari-finanza/mercati/index.html", unit: "Percent per annum", frequency: "Daily observations; monthly publication cycle", reuse: "Banca d'Italia terms apply; no written permission for reproduction on information systems has been verified. BIVA upstream vendors are not itemized, so this does not confirm Bloomberg is absent. The operator-selected personal-interview purpose records intended use only and does not establish reuse rights." },
  Germany: { agency: "Deutsche Bundesbank", series_id: "BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", definition: "10-year residual-maturity yield derived from the Svensson term structure for listed Federal securities; not a single benchmark bond.", source_url: "https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/zinssaetze-und-renditen/taegliche-zinsstruktur-fuer-boersennotierte-bundeswertpapiere-650724", unit: "Percent per annum", frequency: "Daily", reuse: "Retain published observations and attribution: Source: Deutsche Bundesbank." },
  Japan: { agency: "Ministry of Finance Japan", series_id: "MOF Interest Rate table, 10Y column", definition: "Semiannual-compound 10-year constant-maturity JGB yield. MOF uses secondary-market prices based on JSDA Reference Statistical Prices (Yields). Current-month MOF values take precedence on overlap.", source_url: "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm", unit: "Percent per annum", frequency: "Daily", reuse: "MOF Public Data License Version 1.0 applies unless individually indicated otherwise; cite MOF." },
};

export function parseCsv(text: string, separator = ","): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (c === separator && !quoted) { row.push(cell); cell = ""; }
    else if ((c === "\n" || c === "\r") && !quoted) {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); if (row.some((v) => v.trim())) rows.push(row);
      row = []; cell = "";
    } else cell += c;
  }
  if (quoted) throw new Error("Official export contains an unterminated CSV quote");
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

export function dateIso(year: number, month: number, day: number): string {
  const date = new Date(Date.UTC(year, month - 1, day));
  if (year < 1900 || date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) throw new Error("Invalid calendar date in official export");
  return date.toISOString().slice(0, 10);
}

function numberValue(value: string | undefined): number | null {
  const text = (value ?? "").trim();
  if (!text || [".", "-", "n/a", "na", "null", "nan"].includes(text.toLowerCase())) return null;
  if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text)) throw new Error(`Invalid numeric observation in official export: ${text.slice(0, 24)}`);
  const result = Number(text);
  if (!Number.isFinite(result)) throw new Error("Non-finite official observation");
  return result;
}

export function normalizedRows(rows: Observation[], now: Date): Observation[] {
  const seen = new Map<string, number>();
  const today = now.toISOString().slice(0, 10);
  for (const row of rows) {
    if (row.date < "2020-01-01") continue;
    if (row.date > today) throw new Error("Official export contains a future observation");
    if (seen.has(row.date) && seen.get(row.date) !== row.value) throw new Error("Conflicting duplicate official observations");
    seen.set(row.date, row.value);
  }
  if (seen.size < 100) throw new Error("Official full-history export is unexpectedly short; last-good data preserved");
  return [...seen].sort(([a], [b]) => a.localeCompare(b)).map(([date, value]) => ({ date, value }));
}

async function download(name: string, url: string): Promise<RawDownload> {
  if (!AGENCY_HOSTS.has(new URL(url).hostname)) throw new Error("Unexpected source hostname");
  const response = await fetch(url, { signal: AbortSignal.timeout(30000), cache: "no-store", headers: { Accept: "text/csv, text/plain;q=0.9, */*;q=0.1" } });
  if (!response.ok) throw new Error(`Official download returned HTTP ${response.status}`);
  if (!AGENCY_HOSTS.has(new URL(response.url || url).hostname)) throw new Error("Official download redirected outside agency allowlist");
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!bytes.length || bytes.length > MAX_DOWNLOAD_BYTES) throw new Error("Official export has an unexpected size");
  return { name, url, bytes };
}

function csv(raw: RawDownload) { return parseCsv(new TextDecoder("utf-8").decode(raw.bytes).replace(/^\uFEFF/, "")); }

export async function fetchCountry(country: OfficialCountry, now = new Date()): Promise<CountryDownload> {
  let rows: Observation[] = [], raw: RawDownload[] = [];
  if (country === "US") {
    raw = await Promise.all(Array.from({ length: now.getUTCFullYear() - 2019 }, (_, i) => {
      const year = 2020 + i;
      return download(`us_treasury_${year}.csv`, `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/${year}/all?type=daily_treasury_yield_curve&field_tdr_date_value=${year}`);
    }));
    for (const file of raw) {
      const [header, ...body] = csv(file);
      const dateCol = header.indexOf("Date"), yieldCol = header.indexOf("10 Yr");
      if (dateCol < 0 || yieldCol < 0) throw new Error("Treasury export lacks Date/10 Yr columns");
      for (const row of body) {
        if (!row[dateCol]?.trim()) continue;
        const parts = row[dateCol].split("/").map(Number);
        if (parts.length !== 3) throw new Error("Unexpected Treasury date format");
        const value = numberValue(row[yieldCol]);
        if (value !== null) rows.push({ date: dateIso(parts[2] < 100 ? parts[2] + 2000 : parts[2], parts[0], parts[1]), value });
      }
    }
  } else if (country === "UK") {
    raw = [await download("uk_boe_iudmnpy.csv", "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDMNPY&CSVF=TN&UsingCodes=Y")];
    const [header, ...body] = csv(raw[0]);
    const dateCol = header.indexOf("DATE"), yieldCol = header.indexOf("IUDMNPY");
    if (dateCol < 0 || yieldCol < 0) throw new Error("BoE export lacks DATE/IUDMNPY columns");
    const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
    for (const row of body) {
      if (!row[dateCol]?.trim()) continue;
      const match = row[dateCol].trim().match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$/);
      if (!match) throw new Error("Unexpected BoE date format");
      const value = numberValue(row[yieldCol]);
      if (value !== null) rows.push({ date: dateIso(Number(match[3]), months.indexOf(match[2].toLowerCase()) + 1, Number(match[1])), value });
    }
  } else if (country === "France") {
    raw = [await download("france_bdf_tec.csv", "https://webstat.banque-france.fr/export/csv-columns/en/selection/5385693")];
    const table = csv(raw[0]);
    const idRow = table.findIndex((row) => row.includes(OFFICIAL_SOURCES.France.series_id));
    const yieldCol = idRow >= 0 ? table[idRow].indexOf(OFFICIAL_SOURCES.France.series_id) : -1;
    if (yieldCol < 0) throw new Error("Banque de France export lacks the exact TEC10 series ID");
    for (const row of table.slice(idRow + 1)) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(row[0] ?? "")) continue;
      const parts = row[0].split("-").map(Number), value = numberValue(row[yieldCol]);
      if (value !== null) rows.push({ date: dateIso(parts[0], parts[1], parts[2]), value });
    }
  } else if (country === "Italy") {
    raw = [await download("italy_bdi_bmk0200.zip", "https://a2a.bancaditalia.it/infostat/dataservices/export/IT/CSV/ALL/CUBE/BANKITALIA/DIFF/BMK0200")];
    const { unzipSync } = await import("fflate");
    const files = unzipSync(raw[0].bytes, { filter: (file) => file.name === "BMK0200_DATA.csv" && file.originalSize <= 16 * 1024 * 1024 });
    const data = files["BMK0200_DATA.csv"];
    if (!data) throw new Error("Banca d'Italia archive lacks the expected bounded BMK0200 data table");
    const [header, ...body] = parseCsv(new TextDecoder().decode(data).replace(/^\uFEFF/, ""), ";");
    const dateCol = header.indexOf("DATA_OSS"), yieldCol = header.indexOf(OFFICIAL_SOURCES.Italy.series_id);
    if (dateCol < 0 || yieldCol < 0) throw new Error("Banca d'Italia table lacks the exact daily 10-year BTP series");
    for (const row of body) {
      if (!row[dateCol]?.trim()) continue;
      const parts = row[dateCol].split("/").map(Number);
      if (parts.length !== 3) throw new Error("Unexpected Banca d'Italia date format");
      const value = numberValue(row[yieldCol]?.replace(",", "."));
      if (value !== null) rows.push({ date: dateIso(parts[0], parts[1], parts[2]), value });
    }
  } else if (country === "Germany") {
    raw = [await download("germany_bundesbank_10y.csv", "https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en")];
    for (const row of csv(raw[0])) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(row[0] ?? "")) continue;
      const parts = row[0].split("-").map(Number), value = numberValue(row[1]);
      if (value !== null) rows.push({ date: dateIso(parts[0], parts[1], parts[2]), value });
    }
  } else {
    raw = await Promise.all([
      download("japan_mof_all.csv", "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"),
      download("japan_mof_current.csv", "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"),
    ]);
    const combined = new Map<string, number>();
    for (const file of raw) {
      const table = csv(file), headerIndex = table.findIndex((row) => row[0]?.trim() === "Date");
      const yieldCol = table[headerIndex]?.indexOf("10Y") ?? -1;
      if (headerIndex < 0 || yieldCol < 0) throw new Error("MOF export lacks Date/10Y columns");
      for (const row of table.slice(headerIndex + 1)) {
        if (!/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(row[0]?.trim() ?? "")) continue;
        const parts = row[0].trim().split("/").map(Number), value = numberValue(row[yieldCol]);
        if (value !== null) combined.set(dateIso(parts[0], parts[1], parts[2]), value);
      }
    }
    rows = [...combined].map(([date, value]) => ({ date, value }));
  }
  return { rows: normalizedRows(rows, now), raw };
}

export function base64(bytes: Uint8Array): string {
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x4000) text += String.fromCharCode(...bytes.subarray(i, i + 0x4000));
  return btoa(text);
}
