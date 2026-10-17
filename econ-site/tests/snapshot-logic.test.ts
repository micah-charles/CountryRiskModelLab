import assert from "node:assert/strict";
import test from "node:test";
import { ALL_BOND_COUNTRIES, PERSONAL_INTERVIEW_PURPOSE, assertNoHistoryLoss, collectChanges, flattenSnapshot, hostedBondCountriesForPurpose, validateSnapshot } from "../lib/snapshot-logic.ts";

function bondSnapshot(values: Record<string, Array<{ date: string; value: number | null }>> = {}) {
  const countries = ["US", "UK", "Germany", "Japan"];
  return {
    schemaVersion: 1,
    datasetKey: "bond-yields",
    periodStart: "2020-01-01",
    retrievedAt: "2026-10-17T12:00:00Z",
    historyComplete: true,
    missingValuePolicy: "blank-no-fill",
    series: Object.fromEntries(countries.map((country) => [country, values[country] ?? [{ date: "2020-01-02", value: 1.2 }, { date: "2020-01-03", value: 1.3 }]])),
    sources: Object.fromEntries(countries.map((country) => [country, { sourceUrl: `https://example.test/${country}`, seriesId: country }])),
    sourceStatus: Object.fromEntries(countries.map((country) => [country, { status: "current" }])),
  };
}

test("revision diff detects changes to non-last bond observations", () => {
  const before = bondSnapshot();
  const after = bondSnapshot({ US: [{ date: "2020-01-02", value: 1.2 }, { date: "2020-01-03", value: 1.5 }, { date: "2020-01-04", value: 1.6 }] });
  const changes = collectChanges("bond-yields", before, after, new Date("2026-10-17T12:00:00Z"));
  assert.equal(changes.all.length, 2);
  assert.ok(changes.all.some((change) => change.recordKey === "US/2020-01-03"));
});

test("recent revision window starts at the first day two months before the current month", () => {
  const before = bondSnapshot({ US: [
    { date: "2026-07-31", value: 1 },
    { date: "2026-08-01", value: 1 },
    { date: "2026-09-30", value: 1 },
    { date: "2026-10-01", value: 1 },
  ] });
  const after = bondSnapshot({ US: before.series.US.map((row) => ({ ...row, value: 2 })) });
  const changes = collectChanges("bond-yields", before, after, new Date("2026-10-31T12:00:00Z"));
  assert.equal(changes.all.length, 4);
  assert.equal(changes.recentCount, 3);
});

test("composite country risk keys include country, indicator, and date and reject duplicates", () => {
  const before = { observations: [{ countryCode: "GBR", indicatorCode: "GDP", year: 2024, value: 100 }, { countryCode: "GBR", indicatorCode: "CPI", year: 2024, value: 3 }] };
  const after = { observations: [{ countryCode: "GBR", indicatorCode: "GDP", year: 2024, value: 101 }, { countryCode: "GBR", indicatorCode: "CPI", year: 2024, value: 3 }] };
  const changes = collectChanges("country-risk", before, after);
  assert.equal(changes.all.length, 1);
  assert.throws(() => collectChanges("country-risk", before, { observations: [before.observations[0], before.observations[0]] }), /Duplicate stable record key/);
});

test("HK demand wide company panels and industry summaries use stock code and financial year", () => {
  const before = {
    companies: [
      { stock_code: "0001", financial_year: 2023, revenue_total: 100, revenue_yoy: 4 },
      { stock_code: "0001", financial_year: 2024, revenue_total: 110, revenue_yoy: 10 },
    ],
    industrySummary: [
      { industry: "Retail", financial_year: 2023, company_count: 1 },
      { industry: "Retail", financial_year: 2024, company_count: 1 },
    ],
  };
  const after = {
    companies: [
      { stock_code: "0001", financial_year: 2023, revenue_total: 100, revenue_yoy: 4 },
      { stock_code: "0001", financial_year: 2024, revenue_total: 115, revenue_yoy: 14 },
    ],
    industrySummary: [
      { industry: "Retail", financial_year: 2023, company_count: 1 },
      { industry: "Retail", financial_year: 2024, company_count: 1 },
    ],
  };
  const changes = collectChanges("hk-demand", before, after);
  assert.equal(changes.all.length, 1);
  assert.equal(changes.all[0].recordKey, "companies/0001/2024");
  assert.equal(flattenSnapshot("hk-demand", before).size, 4);

  const longForm = { companies: [
    { stock_code: "0001", financial_year: 2024, metric_id: "revenue_total", value: 115 },
    { stock_code: "0001", financial_year: 2024, metric_id: "revenue_yoy", value: 14 },
  ] };
  assert.equal(flattenSnapshot("hk-demand", longForm).size, 2);
});

test("bond validation rejects invalid, duplicate, unsorted, or incomplete series", () => {
  assert.throws(() => validateSnapshot("bond-yields", bondSnapshot({ US: [{ date: "2026-02-30", value: 2 }] })), /invalid calendar date/);
  assert.throws(() => validateSnapshot("bond-yields", bondSnapshot({ US: [{ date: "2020-01-03", value: 1 }, { date: "2020-01-03", value: 2 }] })), /unique and strictly ascending/);
  assert.throws(() => validateSnapshot("bond-yields", bondSnapshot({ US: [{ date: "2020-01-03", value: 1 }, { date: "2020-01-02", value: 2 }] })), /unique and strictly ascending/);
  const incomplete = bondSnapshot();
  delete incomplete.series.Japan;
  assert.throws(() => validateSnapshot("bond-yields", incomplete), /coverage is incomplete/);
});

test("only the configured personal-interview purpose enables France and Italy", () => {
  assert.deepEqual(hostedBondCountriesForPurpose(undefined), ["US", "UK", "Germany", "Japan"]);
  assert.deepEqual(hostedBondCountriesForPurpose("fr-it-private"), ["US", "UK", "Germany", "Japan"]);
  assert.deepEqual(hostedBondCountriesForPurpose(PERSONAL_INTERVIEW_PURPOSE), ALL_BOND_COUNTRIES);

  const sixCountries = [...ALL_BOND_COUNTRIES];
  const snapshot = {
    ...bondSnapshot(),
    series: Object.fromEntries(sixCountries.map((country) => [country, [{ date: "2020-01-02", value: 1.2 }]])),
    sources: Object.fromEntries(sixCountries.map((country) => [country, { sourceUrl: `https://example.test/${country}`, seriesId: country }])),
    sourceStatus: Object.fromEntries(sixCountries.map((country) => [country, { status: "current" }])),
    operatorSelectedPurpose: PERSONAL_INTERVIEW_PURPOSE,
    sourceRightsStatus: { France: "not-verified", Italy: "not-verified" },
  };
  assert.doesNotThrow(() => validateSnapshot("bond-yields", snapshot, sixCountries));
  assert.throws(() => validateSnapshot("bond-yields", { ...snapshot, operatorSelectedPurpose: null }, sixCountries), /operator-selected purpose/);
  assert.throws(() => validateSnapshot("bond-yields", { ...snapshot, sourceRightsStatus: { France: "verified", Italy: "not-verified" } }, sixCountries), /rights status must remain explicitly not verified/);
});

test("a revised snapshot cannot silently drop historical observations", () => {
  const before = bondSnapshot();
  const after = bondSnapshot({ US: [{ date: "2020-01-03", value: 1.3 }] });
  assert.throws(() => assertNoHistoryLoss("bond-yields", before, after), /history loss is not allowed/);
});
