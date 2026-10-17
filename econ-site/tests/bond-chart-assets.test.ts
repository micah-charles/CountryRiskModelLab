import assert from "node:assert/strict";
import test from "node:test";
import { BOND_CHART_PRESETS, renderBondChartAssets } from "../lib/bond-chart-assets.ts";
import { calendarDateTicks, resolveBondPeriodBounds } from "../lib/bond-chart-logic.ts";
import { BOND_SOURCE_DETAILS, type BondSnapshot } from "../app/data/catalog.ts";

const retrievedAt = "2026-10-17T12:00:00Z";
const snapshot: BondSnapshot = {
  schemaVersion: 1,
  datasetKey: "bond-yields",
  periodStart: "2020-01-01",
  retrievedAt,
  historyComplete: true,
  missingValuePolicy: "blank-no-fill",
  series: {
    US: [
      { date: "2020-01-02", value: 1.82 },
      { date: "2023-10-17", value: 4.83 },
      { date: "2024-01-10", value: 4.01 },
      { date: "2024-01-11", value: null },
      { date: "2024-01-12", value: 3.94 },
      { date: "2026-10-10", value: 4.25 },
    ],
    UK: [
      { date: "2020-01-02", value: 0.76 },
      { date: "2023-10-17", value: 4.72 },
      { date: "2024-01-10", value: 3.91 },
      { date: "2024-01-12", value: 3.82 },
      { date: "2026-10-10", value: 4.12 },
    ],
  },
  sources: { US: BOND_SOURCE_DETAILS.US, UK: BOND_SOURCE_DETAILS.UK },
  sourceStatus: { US: { status: "current" }, UK: { status: "current" } },
};

test("renders five preset image bundles with version-and-content-addressed keys", () => {
  const artifacts = renderBondChartAssets(snapshot, 17, "a".repeat(64));
  assert.equal(BOND_CHART_PRESETS.length, 5);
  assert.equal(artifacts.length, 15);
  for (const period of BOND_CHART_PRESETS) {
    const base = artifacts.find((item) => item.period === period.key && item.country === "base");
    const us = artifacts.find((item) => item.period === period.key && item.country === "US");
    const uk = artifacts.find((item) => item.period === period.key && item.country === "UK");
    assert.ok(base && us && uk);
    assert.match(base.objectKey, /v17\/a{64}\/charts\//);
    assert.match(base.svg, /Government bond yields/);
    assert.match(base.svg, /Retrieved 2026-10-17T12:00:00Z/);
    assert.match(base.svg, /Missing observations remain blank/);
    assert.match(base.svg, /1920/);
    assert.match(base.svg, /stroke-dasharray="7 8"/);
    const endDate = "2026-10-10";
    const startDate = resolveBondPeriodBounds(period.key, "rolling", endDate).startDate;
    assert.equal((base.svg.match(/stroke-dasharray="3 6"/g) ?? []).length, calendarDateTicks(startDate, endDate, "quarterly").length);
    assert.match(base.svg, />0%<\/text>/);
    assert.match(base.svg, />4%<\/text>/);
    assert.match(us.svg, /<path d="M/);
    assert.match(uk.svg, /<path d="M/);
  }
});

test("null observations split a plotted line instead of being filled", () => {
  const assets = renderBondChartAssets(snapshot, 18, "b".repeat(64));
  const us = assets.find((item) => item.period === "since-2020" && item.country === "US")!;
  const path = us.svg.match(/<path d="([^"]*)"/)?.[1] ?? "";
  assert.equal((path.match(/M/g) ?? []).length, 2);
});
