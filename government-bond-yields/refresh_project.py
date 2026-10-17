#!/usr/bin/env python3
"""Refresh official source snapshots and rebuild the normalized daily dataset + SVG."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
START = date(2020, 1, 1)
COUNTRIES = ["US", "UK", "France", "Italy", "Germany", "Japan"]
DISPLAY = {
    "US": ("United States", "#533620", "2 5"),
    "UK": ("United Kingdom", "#DA8738", ""),
    "France": ("France", "#203E5C", "8 5"),
    "Italy": ("Italy", "#55A6B9", "9 5"),
    "Japan": ("Japan", "#2D7953", ""),
    "Germany": ("Germany", "#242424", ""),
}

SOURCES = {
    "US": {
        "agency": "U.S. Department of the Treasury",
        "dataset": "Daily Treasury Par Yield Curve Rates, 10 Yr",
        "series_id": "10 Yr column; Treasury does not assign a separate time-series ID",
        "definition": "10-year par yield read from Treasury's estimated daily par yield curve; based on indicative bid-side quotations for actively traded Treasury securities, not transaction prices. Monotone-convex spline since 2021-12-06; earlier observations use the then-official method.",
        "frequency": "Daily (Treasury business days)", "unit": "Percent per annum",
        "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
        "download_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{YEAR}/all?type=daily_treasury_yield_curve&field_tdr_date_value={YEAR}",
        "reuse": "Public official download; no series-specific licence statement was located. Credit the U.S. Treasury and verify current reuse terms before redistribution. No Bloomberg series/account is used by this project.",
        "raw_files": "us_treasury_2020.csv … us_treasury_{current_year}.csv",
    },
    "UK": {
        "agency": "Bank of England",
        "dataset": "IUDMNPY — Yield from British Government Securities, 10 year Nominal Par Yield",
        "series_id": "IUDMNPY",
        "definition": "10-year nominal par yield from a fitted UK gilt term structure using the Bank's Variable Roughness Penalty model; not the yield of one specific gilt.",
        "frequency": "Daily (working days)", "unit": "Percent per annum",
        "source_url": "https://www.bankofengland.co.uk/statistics/yield-curves",
        "download_url": "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDMNPY&CSVF=TN&UsingCodes=Y",
        "reuse": "Bank of England Database data are made available under the UK Open Government Licence, subject to its stated exclusions and third-party rights. Attribute the Bank of England.",
        "raw_files": "uk_boe_iudmnpy.csv",
    },
    "France": {
        "agency": "Banque de France Webstat (source: Euronext / MTS France)",
        "dataset": "FM — Marché financier, taux; CNO-TEC 10 / TEC10",
        "series_id": "FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA",
        "definition": "Daily 10-year constant-maturity rate (TEC10) for French government bonds; CNO-TEC index calculated and administered by Euronext from MTS France data. Not a single benchmark bond.",
        "frequency": "Daily", "unit": "Percent",
        "source_url": "https://webstat.banque-france.fr/en/catalog/fm/FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA",
        "download_url": "https://webstat.banque-france.fr/export/csv-columns/en/selection/5385693",
        "reuse": "Euronext/AFT terms: values may not be redistributed, sublicensed or used commercially without Euronext's prior written permission. Local analysis only; request permission before sharing the data or derived chart externally.",
        "raw_files": "fr_bdf_tec.csv",
    },
    "Italy": {
        "agency": "Banca d'Italia — Infostat / BDS",
        "dataset": "BMK0200 — Benchmark government securities: gross yields to maturity, daily data",
        "series_id": "MFN_BMK.D.020.922.0.EUR.210",
        "definition": "Gross yield to maturity on Italy's 10-year benchmark BTP (benchmark issue, not a constant-maturity fitted curve). Banca d'Italia metadata says data are processed from various sources (BIVA); the underlying market-data providers are not itemized.",
        "frequency": "Daily; weekends/holidays have no observation", "unit": "Percent; source file retains published precision",
        "source_url": "https://www.bancaditalia.it/statistiche/tematiche/moneta-intermediari-finanza/mercati/index.html",
        "download_url": "https://a2a.bancaditalia.it/infostat/dataservices/export/IT/CSV/ALL/CUBE/BANKITALIA/DIFF/BMK0200",
        "reuse": "Banca d'Italia site terms limit data to personal use, prohibit commercial use and alteration, and require prior written permission for reproduction on information systems. This project is a private local copy; do not redistribute or commercially use. Underlying source vendors are unspecified, so the project cannot certify their absence from BIVA inputs.",
        "raw_files": "it_bdi_bmk0200.zip (original BDS export, including structure/domain/legend)",
    },
    "Germany": {
        "agency": "Deutsche Bundesbank",
        "dataset": "Yields derived from the term structure of interest rates, 10.0-year residual maturity, daily data",
        "series_id": "BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
        "definition": "Yield derived from the Svensson term structure for listed German Federal securities with annual coupon payments at 10.0 years residual maturity; a fitted constant-maturity point, not one current bond.",
        "frequency": "Daily (calendar-date series; non-trading days blank)", "unit": "Percent, published to 2 decimals",
        "source_url": "https://www.bundesbank.de/en/statistics/money-and-capital-markets/securities-issues/no-05-yields-and-indices-on-german-securities",
        "download_url": "https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en",
        "reuse": "Bundesbank permits saving/reproducing information it produced for personal or professional use when not altered, with attribution 'Source: Deutsche Bundesbank'. Source values are retained; this workbook only reorganizes them for analysis.",
        "raw_files": "de_bundesbank_10y.csv",
    },
    "Japan": {
        "agency": "Ministry of Finance Japan (MOF)",
        "dataset": "Interest Rate — 10Y column; historical and current-month CSVs",
        "series_id": "MOF Interest Rate table, tenor column 10Y (no separate series ID published)",
        "definition": "10-year semiannual-compound nominal constant-maturity JGB rate, based on the prevailing secondary-market yield curve at 3 p.m.; source bond yields use JSDA Reference Statistical Prices (Yields). Released next business day.",
        "frequency": "Daily (business days)", "unit": "Percent",
        "source_url": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm",
        "download_url": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv ; https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv",
        "reuse": "MOF states Public Data License Version 1.0 applies unless otherwise indicated. Cite MOF, identify changes, and check individual content restrictions before external reuse.",
        "raw_files": "jp_mof_all.csv and jp_mof_current.csv (current-month values supersede historical overlaps)",
    },
}

DOWNLOAD_HEADERS = {"User-Agent": "Econ-government-bond-yields/1.0 (research; source attribution in project)"}


def fetch(url: str, path: Path) -> None:
    req = urllib.request.Request(url, headers=DOWNLOAD_HEADERS)
    with urllib.request.urlopen(req, timeout=90) as response:
        body = response.read()
    if not body:
        raise RuntimeError(f"Empty response from {url}")
    path.write_bytes(body)


def download_sources() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    current_year = datetime.now(timezone.utc).year
    for year in range(2020, current_year + 1):
        url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}"
        fetch(url, RAW / f"us_treasury_{year}.csv")
    fetch(SOURCES["UK"]["download_url"], RAW / "uk_boe_iudmnpy.csv")
    fetch(SOURCES["France"]["download_url"], RAW / "fr_bdf_tec.csv")
    fetch(SOURCES["Germany"]["download_url"], RAW / "de_bundesbank_10y.csv")
    fetch(SOURCES["Italy"]["download_url"], RAW / "it_bdi_bmk0200.zip")
    fetch("https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv", RAW / "jp_mof_all.csv")
    fetch("https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv", RAW / "jp_mof_current.csv")


def parse_date(s: str, formats: tuple[str, ...]) -> date:
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {s!r}")


def parse_number(s: str, decimal_comma: bool = False) -> float | None:
    s = (s or "").strip()
    if s in {"", ".", "-", "..", "NA", "N/A"}:
        return None
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".")
    value = float(s)
    if not math.isfinite(value):
        return None
    return value


def add(series: dict[str, dict[date, float]], country: str, d: date, value: float | None) -> None:
    if d < START or value is None:
        return
    if d in series[country] and series[country][d] != value:
        raise ValueError(f"Conflicting duplicate for {country} {d}: {series[country][d]} vs {value}")
    series[country][d] = value


def parse_sources() -> tuple[dict[str, dict[date, float]], dict[str, dict]]:
    series = {c: {} for c in COUNTRIES}
    duplicate_rows = Counter()

    for path in sorted(RAW.glob("us_treasury_*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_date = row.get("Date") or ""
                if not raw_date.strip():
                    continue
                d = parse_date(raw_date, ("%m/%d/%Y", "%m/%d/%y"))
                val = parse_number(row.get("10 Yr", ""))
                if d in series["US"]:
                    duplicate_rows["US"] += 1
                add(series, "US", d, val)

    with (RAW / "uk_boe_iudmnpy.csv").open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            d = parse_date(row.get("DATE", ""), ("%d %b %Y",))
            val = parse_number(row.get("IUDMNPY", ""))
            if d in series["UK"]: duplicate_rows["UK"] += 1
            add(series, "UK", d, val)

    with (RAW / "fr_bdf_tec.csv").open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if len(rows) < 7 or rows[0][2] != "Constant maturity rate 10 years" or rows[1][2] != "FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA":
        raise ValueError("France export does not contain the expected 10Y TEC series")
    for row in rows[6:]:
        if not row or not row[0]: continue
        d = parse_date(row[0], ("%Y-%m-%d",))
        val = parse_number(row[2])
        if d in series["France"]: duplicate_rows["France"] += 1
        add(series, "France", d, val)

    with (RAW / "de_bundesbank_10y.csv").open(newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or not re.match(r"^\d{4}-\d{2}-\d{2}$", row[0]): continue
            d = parse_date(row[0], ("%Y-%m-%d",))
            val = parse_number(row[1] if len(row) > 1 else "")
            if d in series["Germany"]: duplicate_rows["Germany"] += 1
            add(series, "Germany", d, val)

    it_zip = RAW / "it_bdi_bmk0200.zip"
    with zipfile.ZipFile(it_zip) as zf:
        data_name = next(n for n in zf.namelist() if n.endswith("_DATA.csv"))
        with io.TextIOWrapper(zf.open(data_name), encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            target = "MFN_BMK.D.020.922.0.EUR.210"
            if target not in (reader.fieldnames or []):
                raise ValueError(f"Italy export lacks {target}")
            for row in reader:
                d = parse_date(row.get("DATA_OSS", ""), ("%Y/%m/%d",))
                val = parse_number(row.get(target, ""), decimal_comma=True)
                if d in series["Italy"]: duplicate_rows["Italy"] += 1
                add(series, "Italy", d, val)

    for filename in ("jp_mof_all.csv", "jp_mof_current.csv"):
        path = RAW / filename
        text = None
        for encoding in ("cp932", "utf-8-sig", "utf-8"):
            try:
                text = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None: raise UnicodeError(f"Could not decode {filename}")
        rows = list(csv.reader(io.StringIO(text)))
        header_idx = next((i for i, row in enumerate(rows) if row and row[0].strip() == "Date"), None)
        if header_idx is None: raise ValueError(f"No Date header in {filename}")
        header = rows[header_idx]
        tenor_idx = header.index("10Y")
        for row in rows[header_idx + 1:]:
            if not row or not row[0].strip() or not re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", row[0].strip()): continue
            d = parse_date(row[0], ("%Y/%m/%d",))
            val = parse_number(row[tenor_idx] if len(row) > tenor_idx else "")
            # The current-month MOF table is authoritative for an overlap.
            if filename == "jp_mof_current.csv" or d not in series["Japan"]:
                if d in series["Japan"]: duplicate_rows["Japan"] += 1
                add(series, "Japan", d, val)

    return series, {c: {"duplicate_date_rows": duplicate_rows[c]} for c in COUNTRIES}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_processed(series: dict[str, dict[date, float]], diagnostics: dict[str, dict]) -> dict:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    all_dates = sorted(set().union(*(set(series[c]) for c in COUNTRIES)))
    if not all_dates:
        raise RuntimeError("No observations found")
    csv_path = PROCESSED / "daily_yields.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", *[f"{c.lower()}_yield_pct" for c in COUNTRIES]])
        for d in all_dates:
            writer.writerow([d.isoformat(), *[series[c].get(d, "") for c in COUNTRIES]])

    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    metadata = {
        "project": "Six-country daily 10-year government bond yields",
        "period_start": START.isoformat(),
        "period_end_latest_available": max(all_dates).isoformat(),
        "retrieved_at_utc": retrieved,
        "missing_value_policy": "Blank source observations remain blank. No interpolation, forward-fill, estimation, or cross-source substitution.",
        "source_value_policy": "Yield values are transcribed without rounding. Calendar alignment only; source-specific yields are not harmonised.",
        "countries": {},
        "raw_file_sha256": {},
    }
    for path in sorted(RAW.iterdir()):
        if path.is_file(): metadata["raw_file_sha256"][path.name] = sha256(path)
    for c in COUNTRIES:
        ds = sorted(series[c])
        metadata["countries"][c] = {
            **SOURCES[c],
            "first_observation": ds[0].isoformat() if ds else None,
            "latest_observation": ds[-1].isoformat() if ds else None,
            "latest_value_pct": series[c][ds[-1]] if ds else None,
            "observation_count": len(ds),
            "missing_dates_in_union_panel": len(all_dates) - len(ds),
            "duplicate_date_rows": diagnostics[c]["duplicate_date_rows"],
        }
    (PROCESSED / "source_metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report = [
        "# Data validation report",
        "",
        f"- Retrieved (UTC): {retrieved}",
        f"- Period in panel: {all_dates[0].isoformat()} to {all_dates[-1].isoformat()} (source observations; panel starts at the first observed date on/after {START.isoformat()})",
        f"- Rows in aligned union-date panel: {len(all_dates)}",
        "- Missing values remain blank; no forward fill, interpolation or estimate was used.",
        "- Numeric range check: every source yield must be between -2% and 10%; the range is deliberately broad and only catches obvious parse errors.",
        "",
        "| Country | Observations | First | Latest | Latest (%) | Min (%) | Max (%) | Blank cells in date union | Duplicate date rows |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for c in COUNTRIES:
        vals = list(series[c].values())
        if not vals: raise RuntimeError(f"Missing all data for {c}")
        if min(vals) < -2 or max(vals) > 10:
            raise ValueError(f"Out-of-range values in {c}: {min(vals)} to {max(vals)}")
        ds = sorted(series[c])
        report.append(f"| {c} | {len(vals)} | {ds[0]} | {ds[-1]} | {series[c][ds[-1]]:.5f} | {min(vals):.5f} | {max(vals):.5f} | {len(all_dates)-len(vals)} | {diagnostics[c]['duplicate_date_rows']} |")
    report.extend([
        "",
        "## Integrity checks",
        "",
        "- All six sources produced at least one observation on/after 2020-01-01.",
        "- Conflicting duplicate dates cause refresh to stop; identical repeats are counted.",
        "- Country observations are sourced from the original agency exports listed in `source_metadata.json`.",
        "- A blank cell means the source did not publish a value for that date; it is not a zero.",
        "- Italy's official series is published by Banca d'Italia and its upstream market-data providers are not itemized in the metadata.",
    ])
    (PROCESSED / "validation_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    write_svg(series, all_dates[-1])
    return metadata


def write_svg(series: dict[str, dict[date, float]], latest_date: date) -> None:
    width, height = 1920, 1080
    left, right, top, bottom = 155, 1880, 125, 845
    y_min, y_max = -2.0, 6.0
    start_ord, end_ord = START.toordinal(), latest_date.toordinal()
    def x(d: date) -> float: return left + (d.toordinal() - start_ord) / (end_ord - start_ord) * (right - left)
    def y(v: float) -> float: return bottom - (v - y_min) / (y_max - y_min) * (bottom - top)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#1d1d1d}.axis{font-size:22px}.small{font-size:18px}.title{font-size:34px;font-weight:600}.legend{font-size:22px}</style>',
           '<text x="960" y="64" text-anchor="middle" class="title">10-year government bond yields (%)</text>',
           f'<text x="960" y="97" text-anchor="middle" class="small">Daily observations · 2020-01-01 to {latest_date.isoformat()} · latest available date differs by source</text>']
    # Grid and y-axis labels.
    for tick in range(-2, 7):
        yy = y(float(tick))
        stroke = "#b9b9b9" if tick == 0 else "#e1e1e1"
        sw = 2 if tick == 0 else 1
        out.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" stroke="{stroke}" stroke-width="{sw}"/>')
        out.append(f'<text x="{left-18}" y="{yy+7:.2f}" text-anchor="end" class="axis">{tick}</text>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#333" stroke-width="2"/>')
    out.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#333" stroke-width="2"/>')
    out.append(f'<text x="47" y="{(top+bottom)/2:.0f}" transform="rotate(-90 47 {(top+bottom)/2:.0f})" text-anchor="middle" class="axis">Percent</text>')
    month = date(2020, 1, 1)
    while month <= latest_date:
        xx = x(month)
        out.append(f'<line x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{bottom}" stroke="#eeeeee" stroke-width="1"/>')
        out.append(f'<text x="{xx:.2f}" y="{bottom+32}" text-anchor="middle" class="axis">{month:%m/%Y}</text>')
        month = date(month.year + 1, 1, 1) if month.month == 7 else date(month.year, 7, 1)
    # Each path joins only successive actual published observations.
    for c in COUNTRIES:
        name, color, dash = DISPLAY[c]
        points = [(d, v) for d, v in sorted(series[c].items())]
        pathdata = " ".join(("M" if i == 0 else "L") + f"{x(d):.2f},{y(v):.2f}" for i, (d, v) in enumerate(points))
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<path d="{pathdata}" fill="none" stroke="{color}" stroke-width="3.2" stroke-linejoin="round" stroke-linecap="round"{dash_attr}/>')
    # Legend in two rows, mirroring the reference chart.
    legend_y = 918
    items = [("US", "United States"), ("UK", "United Kingdom"), ("France", "France"), ("Italy", "Italy"), ("Japan", "Japan"), ("Germany", "Germany")]
    col_x = [335, 960, 1565]
    for idx, (c, label) in enumerate(items):
        row, col = divmod(idx, 3)
        xx, yy = col_x[col], legend_y + row * 46
        _, color, dash = DISPLAY[c]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        out.append(f'<line x1="{xx}" y1="{yy-7}" x2="{xx+54}" y2="{yy-7}" stroke="{color}" stroke-width="4"{dash_attr}/>')
        out.append(f'<text x="{xx+68}" y="{yy}" class="legend">{escape(label)}</text>')
    out.append('<text x="960" y="1034" text-anchor="middle" class="small">Definitions differ by country; missing source dates are left blank. No values are interpolated or carried forward.</text>')
    out.append('</svg>')
    (OUTPUTS / "government_bond_yields_2020_latest.svg").write_text("\n".join(out), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-download", action="store_true", help="Rebuild from already saved data/raw snapshots")
    args = parser.parse_args()
    if not args.no_download:
        download_sources()
    for required in ("uk_boe_iudmnpy.csv", "fr_bdf_tec.csv", "de_bundesbank_10y.csv", "it_bdi_bmk0200.zip", "jp_mof_all.csv", "jp_mof_current.csv"):
        if not (RAW / required).exists():
            raise FileNotFoundError(f"Missing raw file {RAW / required}")
    if not list(RAW.glob("us_treasury_*.csv")):
        raise FileNotFoundError("No U.S. Treasury yearly CSV files in data/raw")
    series, diagnostics = parse_sources()
    metadata = write_processed(series, diagnostics)
    print(f"Wrote {PROCESSED / 'daily_yields.csv'} ({metadata['period_start']} to {metadata['period_end_latest_available']})")
    print(f"Wrote {OUTPUTS / 'government_bond_yields_2020_latest.svg'}")
    for c in COUNTRIES:
        m = metadata["countries"][c]
        print(f"{c}: {m['observation_count']} observations, latest {m['latest_observation']} = {m['latest_value_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
