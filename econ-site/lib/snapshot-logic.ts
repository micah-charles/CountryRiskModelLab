export const DATASET_KEYS = ["bond-yields", "country-risk", "research-cases", "hk-demand", "catalog"] as const;
export type DatasetKey = (typeof DATASET_KEYS)[number];
export type SnapshotObject = Record<string, unknown>;

export const DEFAULT_HOSTED_BOND_COUNTRIES = ["US", "UK", "Germany", "Japan"] as const;
export const ALL_BOND_COUNTRIES = ["US", "UK", "France", "Italy", "Germany", "Japan"] as const;
export const PERSONAL_INTERVIEW_PURPOSE = "personal-interview" as const;
const MAX_SNAPSHOT_BYTES = 3 * 1024 * 1024;

export function hostedBondCountriesForPurpose(purpose: unknown): readonly string[] {
  return purpose === PERSONAL_INTERVIEW_PURPOSE ? ALL_BOND_COUNTRIES : DEFAULT_HOSTED_BOND_COUNTRIES;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function validDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}

function validTimestamp(value: unknown): value is string {
  return typeof value === "string"
    && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/.test(value)
    && Number.isFinite(Date.parse(value));
}

function compositeKey(datasetKey: DatasetKey, field: string, row: Record<string, unknown>): string | null {
  const get = (...names: string[]) => names.map((name) => row[name]).find((value) => value !== undefined && value !== null && value !== "");
  const join = (...parts: unknown[]) => parts.every((part) => part !== undefined && part !== null && part !== "")
    ? parts.map(String).join("/")
    : null;

  if (field === "observations") {
    const key = join(
      get("countryCode", "country_code", "country"),
      get("indicatorId", "indicator_id", "indicatorCode", "indicator_code", "indicator"),
      get("date", "period", "year", "time", "observationDate", "observation_date"),
    );
    const frequency = get("frequency", "frequencyCode", "frequency_code");
    return key ? `${key}${frequency === undefined ? "" : `/${String(frequency)}`}` : null;
  }
  if (field === "cases") return join(get("case_id", "caseId", "id"));
  if (field === "companies") {
    if (datasetKey === "hk-demand") {
      const identity = join(
        get("stock_code", "stockCode", "company_code", "companyCode", "ticker", "company"),
        get("financial_year", "financialYear", "fiscal_year", "fiscalYear", "year"),
      );
      const metric = get("metric_id", "metricId", "metric");
      return identity ? `${identity}${metric === undefined ? "" : `/${String(metric)}`}` : null;
    }
  }
  if (field === "evidence") {
    return join(
      get("stock_code", "stockCode", "company_code", "companyCode"),
      get("financial_year", "financialYear", "year"),
      get("metric", "metric_id", "metricId"),
    );
  }
  if (field === "indicators") return join(get("indicator_id", "indicatorId", "id", "code"));
  if (field === "formulas") return join(get("formula_id", "formulaId", "id", "key"));
  if (field === "events" || field === "timeline") {
    return join(get("event_id", "eventId", "id"), get("date", "period", "year"));
  }
  if (field === "industrySummary" || field === "industry_summary") {
    return join(get("industry_id", "industryId", "industry", "sector"), get("financial_year", "financialYear", "year", "period", "date"));
  }

  // Dataset-specific identifiers are preferred over serialized contents, which
  // would make a changed record appear as a deletion plus an unrelated insert.
  const known = get("id", "key", "source_id", "sourceId", "record_id", "recordId");
  if (known !== undefined) return String(known);
  if (datasetKey === "hk-demand") {
    return join(get("stock_code", "stockCode", "company_code", "companyCode"), get("year", "period", "date"));
  }
  return null;
}

export function flattenSnapshot(datasetKey: DatasetKey, value: unknown): Map<string, string> {
  const result = new Map<string, string>();
  if (!isObject(value)) return result;
  const snapshot = value;
  const insert = (key: string, row: unknown) => {
    if (result.has(key)) throw new Error(`Duplicate stable record key: ${key}`);
    result.set(key, JSON.stringify(row));
  };

  if (datasetKey === "bond-yields") {
    const series = snapshot.series;
    if (!isObject(series)) return result;
    for (const [country, rows] of Object.entries(series)) {
      if (!Array.isArray(rows)) continue;
      for (const row of rows) {
        if (!isObject(row)) continue;
        insert(`${country}/${String(row.date)}`, row);
      }
    }
    return result;
  }

  for (const field of ["observations", "cases", "companies", "evidence", "events", "timeline", "industrySummary", "industry_summary", "indicators", "formulas"] as const) {
    const rows = snapshot[field];
    if (!Array.isArray(rows)) continue;
    rows.forEach((row, index) => {
      if (!isObject(row)) throw new Error(`${field}[${index}] must be an object`);
      const key = compositeKey(datasetKey, field, row);
      if (!key) throw new Error(`${field}[${index}] is missing a stable identifier`);
      insert(`${field}/${key}`, row);
    });
  }
  if (!result.size) insert("snapshot", snapshot);
  return result;
}

export function validateSnapshot(datasetKey: DatasetKey, value: unknown, allowedBondCountries: readonly string[] = DEFAULT_HOSTED_BOND_COUNTRIES): asserts value is SnapshotObject {
  if (!isObject(value)) throw new Error("snapshot must be a JSON object");
  const snapshot = value;
  if (datasetKey === "bond-yields") {
    if (snapshot.datasetKey !== "bond-yields") throw new Error("bond-yields snapshot must declare datasetKey=bond-yields");
    if (snapshot.missingValuePolicy !== "blank-no-fill") throw new Error("bond-yields snapshot must declare missingValuePolicy=blank-no-fill");
    if (!validDate(snapshot.periodStart) || snapshot.periodStart > "2020-01-31") throw new Error("bond-yields snapshot must cover the 2020 start of the requested period");
    if (!validTimestamp(snapshot.retrievedAt)) throw new Error("bond-yields snapshot must include an ISO UTC retrieval timestamp");
    if (snapshot.historyComplete !== true) throw new Error("bond-yields snapshot must declare historyComplete=true");
    if (!isObject(snapshot.series)) throw new Error("bond-yields snapshot must contain a series object");
    const countries = Object.keys(snapshot.series);
    const missing = allowedBondCountries.filter((country) => !countries.includes(country));
    const extra = countries.filter((country) => !allowedBondCountries.includes(country));
    if (missing.length || extra.length) throw new Error(`Bond snapshot country coverage is incomplete (missing: ${missing.join(", ") || "none"}; unsupported: ${extra.join(", ") || "none"}).`);
    if (allowedBondCountries.includes("France") || allowedBondCountries.includes("Italy")) {
      if (snapshot.operatorSelectedPurpose !== PERSONAL_INTERVIEW_PURPOSE) {
        throw new Error("France and Italy snapshots must record the configured operator-selected purpose.");
      }
      if (!isObject(snapshot.sourceRightsStatus)
        || snapshot.sourceRightsStatus.France !== "not-verified"
        || snapshot.sourceRightsStatus.Italy !== "not-verified") {
        throw new Error("France and Italy source rights status must remain explicitly not verified.");
      }
    }
    if (!isObject(snapshot.sources)) throw new Error("bond-yields snapshot must include source definitions");
    if (!isObject(snapshot.sourceStatus)) throw new Error("bond-yields snapshot must include per-source status");
    for (const country of allowedBondCountries) {
      const rows = snapshot.series[country];
      if (!Array.isArray(rows) || rows.length === 0) throw new Error(`series.${country} must contain observations`);
      let previousDate = "";
      for (const [index, row] of rows.entries()) {
        if (!isObject(row)) throw new Error(`series.${country}[${index}] is invalid`);
        if (!validDate(row.date)) throw new Error(`series.${country}[${index}] has an invalid calendar date`);
        if (row.date <= previousDate) throw new Error(`series.${country} dates must be unique and strictly ascending`);
        if (row.value !== null && (typeof row.value !== "number" || !Number.isFinite(row.value))) {
          throw new Error(`series.${country}[${index}] must have a finite numeric value or null`);
        }
        previousDate = row.date;
      }
      if (rows[0].date > "2020-01-31") throw new Error(`series.${country} has no observations near the requested 2020 start`);
      const source = snapshot.sources[country];
      if (!isObject(source) || typeof source.sourceUrl !== "string" || typeof source.seriesId !== "string") {
        throw new Error(`sources.${country} must include seriesId and sourceUrl`);
      }
      const status = snapshot.sourceStatus[country];
      if (!isObject(status) || !["current", "stale"].includes(String(status.status))) {
        throw new Error(`sourceStatus.${country} must be current or stale; failed sources cannot be published`);
      }
    }
  }

  // This also rejects ambiguous rows before any version or diff is written.
  flattenSnapshot(datasetKey, snapshot);
  if (new TextEncoder().encode(JSON.stringify(snapshot)).byteLength > MAX_SNAPSHOT_BYTES) {
    throw new Error(`snapshot exceeds the ${MAX_SNAPSHOT_BYTES} byte limit`);
  }
}

export function collectChanges(datasetKey: DatasetKey, before: unknown, after: unknown, now = new Date()) {
  const oldMap = flattenSnapshot(datasetKey, before);
  const newMap = flattenSnapshot(datasetKey, after);
  const keys = new Set([...oldMap.keys(), ...newMap.keys()]);
  const all: Array<{ recordKey: string; beforeJson: string | null; afterJson: string | null; date: string | null }> = [];
  for (const key of keys) {
    const oldValue = oldMap.get(key);
    const newValue = newMap.get(key);
    if (oldValue === newValue) continue;
    const dateMatch = key.match(/\b\d{4}-\d{2}-\d{2}\b/);
    all.push({ recordKey: key, beforeJson: oldValue ?? null, afterJson: newValue ?? null, date: dateMatch?.[0] ?? null });
  }
  const cutoffDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 2, 1)).toISOString().slice(0, 10);
  return { all, recentCount: all.filter((change) => change.date && change.date >= cutoffDate).length };
}

export function assertNoHistoryLoss(datasetKey: DatasetKey, before: unknown, after: unknown) {
  const oldMap = flattenSnapshot(datasetKey, before);
  const newMap = flattenSnapshot(datasetKey, after);
  const removed = [...oldMap.keys()].filter((key) => !newMap.has(key));
  if (removed.length) throw new Error(`Snapshot would remove ${removed.length} existing record(s); history loss is not allowed.`);
}
