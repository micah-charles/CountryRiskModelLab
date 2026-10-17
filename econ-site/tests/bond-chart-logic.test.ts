import assert from "node:assert/strict";
import test from "node:test";
import { buildBondChartModel, calendarDateTicks, exactYieldAtDate, formatYieldTick, integerYieldDomain, nearestPublishedDate, resolveBondPeriodBounds } from "../lib/bond-chart-logic.ts";

test("rolling periods shift by exact calendar years and clamp leap days", () => {
  assert.deepEqual(resolveBondPeriodBounds("last-1-year", "rolling", "2024-02-29"), {
    startDate: "2023-02-28", endDate: "2024-02-29", mode: "rolling",
  });
  assert.deepEqual(resolveBondPeriodBounds("last-3-years", "rolling", "2024-10-16"), {
    startDate: "2021-10-16", endDate: "2024-10-16", mode: "rolling",
  });
});

test("calendar periods count the current year and fixed periods ignore the window toggle", () => {
  assert.deepEqual(resolveBondPeriodBounds("last-3-years", "calendar", "2024-02-29"), {
    startDate: "2022-01-01", endDate: "2024-02-29", mode: "calendar",
  });
  assert.deepEqual(resolveBondPeriodBounds("year-to-date", "rolling", "2024-02-29"), {
    startDate: "2024-01-01", endDate: "2024-02-29", mode: "fixed",
  });
  assert.deepEqual(resolveBondPeriodBounds("since-2020", "calendar", "2024-02-29"), {
    startDate: "2020-01-01", endDate: "2024-02-29", mode: "fixed",
  });
});

test("quarterly and semiannual x-axis ticks align to calendar dates", () => {
  assert.deepEqual(calendarDateTicks("2024-02-15", "2024-12-12", "quarterly"), ["2024-04-01", "2024-07-01", "2024-10-01"]);
  assert.deepEqual(calendarDateTicks("2024-02-15", "2024-12-12", "semiannual"), ["2024-07-01"]);
  assert.deepEqual(calendarDateTicks("2024-01-01", "2024-07-01", "semiannual"), ["2024-01-01", "2024-07-01"]);
});

test("yield axis uses integer percentage ticks across zero and labels whole percentages", () => {
  const domain = integerYieldDomain([-0.2, 0.05, 1.7]);
  assert.equal(domain.min, -1);
  assert.equal(domain.max, 2);
  assert.deepEqual(domain.ticks, [-1, 0, 1, 2]);
  assert.equal(formatYieldTick(6), "6%");
  assert.equal(formatYieldTick(-1), "-1%");
  assert.equal(formatYieldTick(0.5), "0.5%");
  assert.deepEqual(integerYieldDomain([3.1, 6.2]).ticks, [0, 1, 2, 3, 4, 5, 6, 7]);
  assert.deepEqual(integerYieldDomain([-5.2, -1.1]).ticks, [-6, -5, -4, -3, -2, -1, 0]);
});

test("crosshair snaps to a published date and never interpolates or carries values forward", () => {
  const dates = ["2024-02-29", "2024-03-04", "2024-03-06"];
  assert.equal(nearestPublishedDate(dates, "2024-03-05"), "2024-03-04");
  assert.equal(nearestPublishedDate(dates, "2024-03-02"), "2024-02-29");
  const rows = [{ date: "2024-03-04", value: 3.25 }, { date: "2024-03-06", value: null }];
  assert.equal(exactYieldAtDate(rows, "2024-03-04"), 3.25);
  assert.equal(exactYieldAtDate(rows, "2024-03-05"), null);
  assert.equal(exactYieldAtDate(rows, "2024-03-06"), null);
});

test("chart model preserves null gaps and emits integer ticks plus aligned dates", () => {
  const model = buildBondChartModel({
    US: [
      { date: "2024-01-02", value: -0.1 },
      { date: "2024-02-01", value: null },
      { date: "2024-04-01", value: 1.2 },
    ],
  }, ["US"], "2024-01-01", "2024-06-01", "quarterly");
  assert.equal((model.paths.US?.match(/M/g) ?? []).length, 2);
  assert.deepEqual(model.ticks.map((tick) => tick.value), [-1, 0, 1, 2]);
  assert.deepEqual(model.labels.map((label) => label.date), ["2024-01-01", "2024-04-01"]);
});
