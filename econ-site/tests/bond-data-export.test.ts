import assert from "node:assert/strict";
import test from "node:test";
import { unzipSync } from "fflate";
import { bondExportCsv, bondExportJson, bondExportXlsx, prepareBondExport } from "../lib/bond-data-export.ts";
import { BOND_SOURCE_DETAILS, type BondSnapshot } from "../app/data/catalog.ts";

const countries = ["US", "UK", "France", "Italy", "Germany", "Japan"] as const;
const snapshot: BondSnapshot = {
  schemaVersion: 1,
  datasetKey: "bond-yields",
  periodStart: "2020-01-01",
  retrievedAt: "2026-10-17T15:00:00Z",
  historyComplete: true,
  missingValuePolicy: "blank-no-fill",
  note: "Euronext and Banca d'Italia terms apply; written permission has not been verified.",
  operatorSelectedPurpose: "personal-interview",
  sourceRightsStatus: { France: "not-verified", Italy: "not-verified" },
  series: {
    US: [{ date: "2020-01-02", value: 1.1 }, { date: "2020-01-03", value: null }, { date: "2026-10-10", value: 4.2 }],
    UK: [{ date: "2020-01-02", value: 0.8 }, { date: "2026-10-10", value: 4.0 }],
    France: [{ date: "2020-01-02", value: 0.1 }, { date: "2020-01-03", value: 0.2 }, { date: "2026-10-10", value: 3.4 }],
    Italy: [{ date: "2020-01-02", value: 1.4 }, { date: "2020-01-03", value: 1.5 }, { date: "2026-10-10", value: 3.6001 }],
    Germany: [{ date: "2020-01-02", value: -0.2 }, { date: "2026-10-10", value: 2.8 }],
    Japan: [{ date: "2020-01-02", value: -0.01 }, { date: "2026-10-10", value: 1.2 }],
  },
  sources: Object.fromEntries(countries.map((country) => [country, BOND_SOURCE_DETAILS[country]])),
  sourceStatus: Object.fromEntries(countries.map((country) => [country, { status: "current" }])),
};
const context = { version: 4, snapshotSha256: "a".repeat(64), createdAt: "2026-10-17T15:01:00Z" };

test("exports selected preset and full immutable snapshot dates without filling gaps", () => {
  const full = prepareBondExport(snapshot, context, "full");
  assert.equal(full.startDate, "2020-01-01");
  assert.equal(full.endDate, "2026-10-10");
  assert.deepEqual(full.countries, countries);
  assert.equal(full.dates.length, 3);
  assert.equal(full.series.US?.[1].value, null);
  assert.equal(full.valuesByCountry.get("UK")?.has("2020-01-03"), false);

  const preset = prepareBondExport(snapshot, context, "last-3-years");
  assert.equal(preset.startDate, "2023-10-10");
  assert.deepEqual(preset.dates, ["2026-10-10"]);

  const csv = bondExportCsv(snapshot, context, "full");
  assert.match(csv, /^# snapshot_version=4/m);
  assert.match(csv, /# source=.*Banca d'Italia/);
  assert.match(csv, /Date,US,UK,France,Italy,Germany,Japan\r\n2020-01-02,/);
  assert.match(csv, /2020-01-03,\s*,\s*,0\.2,1\.5/);
  assert.match(csv, /written permission for this owner-only chart has not been verified/);

  const json = JSON.parse(bondExportJson(snapshot, context, "full")) as Record<string, unknown>;
  assert.equal(json.version, 4);
  assert.equal(json.operatorSelectedPurpose, "personal-interview");
  assert.match(String(json.downloadAccessNote), /immutable stored snapshot/);
  assert.deepEqual(json.sourceRightsStatus, { France: "not-verified", Italy: "not-verified" });
  assert.deepEqual((json.series as Record<string, Array<{ value: number | null }>>).US.map((row) => row.value), [1.1, null, 4.2]);
});

test("selected-period export uses the chart's calendar range, mode, date grid, and enabled countries", () => {
  const selected = prepareBondExport(snapshot, context, "last-3-years", {
    periodMode: "calendar",
    dateGrid: "semiannual",
    countries: ["Japan", "US"],
  });
  assert.equal(selected.startDate, "2024-01-01");
  assert.equal(selected.endDate, "2026-10-10");
  assert.deepEqual(selected.countries, ["US", "Japan"]);
  assert.equal(selected.metadata.periodMode, "calendar");
  assert.equal(selected.metadata.dateGrid, "semiannual");
  assert.deepEqual(selected.dates, ["2026-10-10"]);

  const workbook = unzipSync(bondExportXlsx(snapshot, context, "last-3-years", {
    periodMode: "calendar",
    dateGrid: "semiannual",
    countries: ["US", "Japan"],
  }));
  const data = new TextDecoder().decode(workbook["xl/worksheets/sheet1.xml"]);
  const info = new TextDecoder().decode(workbook["xl/worksheets/sheet3.xml"]);
  assert.match(data, /US/);
  assert.match(data, /Japan/);
  assert.doesNotMatch(data, /France/);
  assert.match(info, /calendar/);
  assert.match(info, /semiannual/);
  assert.match(info, /2024-01-01/);
});

test("preserves four-country historical snapshots and keeps source text inert in tabular exports", () => {
  const historical: BondSnapshot = {
    ...snapshot,
    operatorSelectedPurpose: undefined,
    sourceRightsStatus: undefined,
    series: Object.fromEntries(countries.filter((country) => !["France", "Italy"].includes(country)).map((country) => [country, snapshot.series[country]])),
    sources: Object.fromEntries(countries.filter((country) => !["France", "Italy"].includes(country)).map((country) => [country, snapshot.sources[country]])),
    sourceStatus: Object.fromEntries(countries.filter((country) => !["France", "Italy"].includes(country)).map((country) => [country, snapshot.sourceStatus![country]!])),
  };
  const historicalExport = prepareBondExport(historical, { ...context, version: 3 }, "full");
  assert.deepEqual(historicalExport.countries, ["US", "UK", "Germany", "Japan"]);

  const formulaText = '=HYPERLINK("https://example.invalid")';
  const adversarial = {
    ...historical,
    note: formulaText,
    sources: { ...historical.sources, US: { ...historical.sources.US!, reuse: formulaText } },
  };
  const csv = bondExportCsv(adversarial, context, "full");
  const sourceComment = csv.split(/\r?\n/).find((line) => line.startsWith("# source="));
  assert.ok(sourceComment);
  assert.equal(JSON.parse(sourceComment.slice("# source=".length)).reuse, formulaText);
  const noteComment = csv.split(/\r?\n/).find((line) => line.startsWith("# snapshot_note_at_retrieval="));
  assert.ok(noteComment);
  assert.equal(JSON.parse(noteComment.slice("# snapshot_note_at_retrieval=".length)), formulaText);
  assert.equal(csv.split(/\r?\n/).some((line) => line.startsWith(formulaText)), false);

  const archive = unzipSync(bondExportXlsx(adversarial, context, "full"));
  const sourceXml = new TextDecoder().decode(archive["xl/worksheets/sheet2.xml"]);
  const snapshotXml = new TextDecoder().decode(archive["xl/worksheets/sheet3.xml"]);
  assert.match(sourceXml, /t="inlineStr"/);
  assert.match(sourceXml, /=HYPERLINK\(&quot;https:\/\/example\.invalid&quot;\)/);
  assert.doesNotMatch(sourceXml, /<f(?:\s|>)/i);
  assert.match(snapshotXml, /t="inlineStr"/);
  assert.match(snapshotXml, /=HYPERLINK\(&quot;https:\/\/example\.invalid&quot;\)/);
  assert.doesNotMatch(snapshotXml, /<f(?:\s|>)/i);
});

test("Excel export contains all six sources and preserves null and absent values as blank cells", () => {
  const archive = unzipSync(bondExportXlsx(snapshot, context, "full"));
  const decode = (file: string) => new TextDecoder().decode(archive[file]);
  const data = decode("xl/worksheets/sheet1.xml");
  const sources = decode("xl/worksheets/sheet2.xml");
  const snapshotInfo = decode("xl/worksheets/sheet3.xml");
  assert.match(data, /<t xml:space="preserve">France<\/t>/);
  assert.match(data, /<c r="B2"><v>1\.1<\/v><\/c>/);
  assert.match(data, /<c r="E4"><v>3\.6001<\/v><\/c>/);
  assert.doesNotMatch(data, /r="B3"/);
  assert.doesNotMatch(data, /r="C3"/);
  assert.match(sources, /Banca d&apos;Italia/);
  assert.match(sources, /not-verified/);
  assert.match(snapshotInfo, /personal-interview/);
  assert.match(snapshotInfo, /written permission has not been verified/);
});
