# Six-country daily 10-year government bond yields

This local research project downloads daily observations for the United States, United Kingdom, France, Italy, Germany and Japan from public official sources, beginning 2020-01-01. It produces an aligned CSV, an Excel workbook with an editable chart and source notes, and high-resolution SVG/PNG charts.

## Current snapshot

Downloaded 2026-10-16 (UTC). The union-date panel contains 1,768 observation dates from 2020-01-02 through 2026-10-16. The requested start date is 2020-01-01; the first published observation in the six series is 2020-01-02.

| Country | Official series / definition | Frequency | Latest observation | Latest yield |
|---|---|---|---:|---:|
| United States | Treasury 10 Yr par yield from the daily Treasury par curve | Daily | 2026-10-16 | 5.090% |
| United Kingdom | Bank of England IUDMNPY, 10-year nominal par yield from fitted gilt curve | Daily | 2026-10-14 | 5.383% |
| France | Banque de France Webstat / Euronext TEC10, 10-year constant maturity | Daily | 2026-10-16 | 4.794% |
| Italy | Banca d'Italia BMK0200, gross yield to maturity on 10-year benchmark BTP | Daily | 2026-09-30 | 4.58875% |
| Germany | Bundesbank 10-year residual-maturity yield derived from the Svensson term structure | Daily | 2026-10-16 | 3.450% |
| Japan | MOF 10Y constant-maturity JGB rate, semiannual-compound basis | Daily | 2026-10-15 | 2.948% |

Yields are percent per annum, using each agency's published precision. These are not six perfectly harmonised measures: some are constant-maturity fitted-curve points, France is the TEC10 index, Italy is a benchmark bond yield, and the US is a par-curve yield. The workbook's `Sources` tab and `data/processed/source_metadata.json` contain the full series identifiers, definitions, source URLs, retrieval timestamp and reuse notes.

## Data integrity and comparison limits

- The project uses no Bloomberg terminal account, Bloomberg download or Bloomberg-branded time series.
- Italy's published Bank of Italy table is identified as BIVA, “processed by Bank of Italy on data from various sources.” Its public metadata does not enumerate upstream market-data providers, so this project cannot certify the upstream vendor list excludes Bloomberg. It does not claim otherwise.
- All six values are taken from official-source exports. The aligned daily CSV keeps published values unchanged and leaves source gaps blank. It does not interpolate, estimate or forward-fill.
- Dates with no yield for one market remain blank in `data/processed/daily_yields.csv` and the workbook. A blank is not zero. Each country has a different trading calendar and publication lag.
- The graph connects consecutive published observations as line segments. It adds no intermediate numeric observations.

## Sources, methods and reuse conditions

### United States

U.S. Department of the Treasury, Daily Treasury Par Yield Curve Rates, `10 Yr` column. The Treasury says constant-maturity par yields are interpolated from a daily par yield curve based on indicative bid-side quotations from the Federal Reserve Bank of New York, not actual transactions. Treasury changed the curve estimation method to a monotone-convex spline on 2021-12-06; earlier observations retain the method official at that time. The rates are publicly downloadable; this project did not find a series-specific reuse licence, so cite the Treasury and confirm current terms before external republication.

- [Treasury daily interest rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates)
- [Treasury methodology description](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_yield_curve_rates)
- Download: yearly CSV snapshots from `data/raw/us_treasury_YYYY.csv`.

### United Kingdom

Bank of England database series `IUDMNPY`, “Yield from British Government Securities, 10 year Nominal Par Yield”. This is a fitted nominal gilt curve point calculated using the Bank's Variable Roughness Penalty model, not an individual gilt's yield. The Bank's database statistics are covered by the UK Open Government Licence unless an explicit third-party exclusion applies; credit the Bank of England.

- [Bank of England yield curves](https://www.bankofengland.co.uk/statistics/yield-curves)
- [Bank of England database series](https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp?C=C6S&CSVF=TT&DAT=ALL&Filter=N&FromSeries=1&ToSeries=50&Travel=NIxIRxSUx&html.x=54&html.y=45)
- [Bank of England reuse terms](https://www.bankofengland.co.uk/legal)
- Download: `data/raw/uk_boe_iudmnpy.csv`.

### France

Banque de France Webstat series `FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA`, daily TEC10. TEC10 is a French government-bond constant-maturity index calculated and administered by Euronext using MTS France market data. It is not a specific benchmark OAT. Euronext/AFT terms say the published values may not be redistributed, sublicensed or used commercially without Euronext's prior written authorisation. Keep these outputs local for private analysis and obtain permission before external distribution or commercial use.

- [Banque de France Webstat series](https://webstat.banque-france.fr/en/catalog/fm/FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA)
- [Agence France Trésor TEC10 methodology and terms](https://www.aft.gouv.fr/en/tec-10-oat)
- [Banque de France legal reuse terms](https://www.banque-france.fr/fr/infos-legales)
- Download: `data/raw/fr_bdf_tec.csv`.

### Italy

Banca d'Italia Infostat cube `BMK0200`, series `MFN_BMK.D.020.922.0.EUR.210`: gross yield to maturity for the daily 10-year benchmark BTP. This is a benchmark-bond yield, not a constant-maturity fitted curve. The source metadata identifies BIVA (“processed by Bank of Italy on data from various sources”) and does not name its upstream market-data providers.

Banca d'Italia's general website copyright terms permit saving/printing for personal use only, prohibit commercial use and alteration of published data, and require prior written permission to reproduce the website or parts of it on information systems. The series is downloaded here only for this private local Econ project; do not redistribute or commercially use the raw series or derived chart without permission. The raw cube export, structure, legend and domain metadata are retained in `data/raw/it_bdi_bmk0200.zip`.

- [Banca d'Italia BMK0200 methodology note](https://www.bancaditalia.it/pubblicazioni/metodi-e-fonti-note/metodi-note-2025/MFN_note-met_it_20250415.pdf)
- [Banca d'Italia financial-markets statistics](https://www.bancaditalia.it/statistiche/tematiche/moneta-intermediari-finanza/mercati/index.html)
- [Banca d'Italia copyright and reuse terms](https://www.bancaditalia.it/footer/copyright/?com.dotmarketing.htmlpage.language=1)
- [Banca d'Italia ESCB statistics reuse policy](https://www.bancaditalia.it/statistiche/condizioni-utilizzo/index.html?com.dotmarketing.htmlpage.language=1) (does not grant rights over third-party data)

### Germany

Deutsche Bundesbank series `BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A`: yield derived from the Svensson term structure for listed Federal securities with annual coupon payments and 10.0 years residual maturity. The data are daily, in percent, published to two decimals. This is a fitted constant-maturity point, not the yield on one current Bund. The Bundesbank permits saving/reproducing its own information for personal or professional use without alteration and requires the credit “Source: Deutsche Bundesbank”; the spreadsheet keeps the published values and reorganises them for comparison.

- [Bundesbank daily term-structure yields](https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/zinssaetze-und-renditen/taegliche-zinsstruktur-fuer-boersennotierte-bundeswertpapiere-650724)
- [Bundesbank series download/API help](https://www.bundesbank.de/en/statistics/time-series-databases/help-for-sdmx-web-service/web-service-interface-data)
- [Bundesbank website terms, section 4](https://www.bundesbank.de/en/homepage/user-information/terms-of-use-642972?index=2)
- Download: `data/raw/de_bundesbank_10y.csv`.

### Japan

Ministry of Finance Japan (MOF), `10Y` column in the daily Interest Rate table. MOF says the rate is the semiannual-compound nominal constant-maturity rate derived from the JGB yield curve using prevailing market prices at 3 p.m.; issue-level yields use JSDA Reference Statistical Prices (Yields). The historical CSV is combined with the current-month CSV, with current-month values taking precedence where dates overlap. MOF applies Public Data License (Version 1.0) unless otherwise indicated; cite MOF and describe any modification.

- [MOF interest-rate methodology FAQ](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm)
- [MOF historical series](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/)
- [MOF copyright/reuse terms](https://www.mof.go.jp/english/about_mof/notice/index.html)
- Downloads: `data/raw/jp_mof_all.csv` and `data/raw/jp_mof_current.csv`.

## Folder contents

- `data/raw/` — source snapshots as downloaded, including the original Italian ZIP cube export.
- `data/processed/daily_yields.csv` — normalized long-period panel with one row per union observation date and blank missing values.
- `data/processed/source_metadata.json` — source definitions, access/usage terms, retrieval timestamp, latest observations and SHA-256 hashes of all raw snapshots.
- `data/processed/validation_report.md` — row counts, missing cells, latest dates, value ranges and duplicate-date check.
- `outputs/government_bond_yields_2020_latest.xlsx` — editable chart, daily data and source/reuse notes.
- `outputs/government_bond_yields_2020_latest.svg` and `.png` — high-resolution figure files.

## Refresh

From this folder, run `./update_all.sh`. It downloads the current official source snapshots, rebuilds the aligned data/metadata/validation report and SVG, rasterizes a 3840 × 2160 PNG, then regenerates the Excel workbook. The workbook builder uses the `@oai/artifact-tool` included in the local Codex workspace runtime; it does not add or vendor external dependencies. If your shell does not expose the bundled Node runtime, run the Python refresh, then run `render_chart_png.mjs` and `build_workbook.mjs` using Codex's bundled Node path.

The refresh rewrites files within this new project folder. It does not edit files elsewhere in the existing Econ project.
