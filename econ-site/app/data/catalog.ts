export type CountryKey = "US" | "UK" | "France" | "Italy" | "Germany" | "Japan";
export type YieldPoint = { date: string; value: number | null };
export type BondSnapshot = {
  schemaVersion: number;
  datasetKey: "bond-yields";
  periodStart: string;
  retrievedAt: string;
  historyComplete: boolean;
  missingValuePolicy: "blank-no-fill";
  operatorSelectedPurpose?: string | null;
  sourceRightsStatus?: Partial<Record<CountryKey, string>>;
  restrictedCountries?: string[];
  note?: string;
  series: Partial<Record<CountryKey, YieldPoint[]>>;
  sources: Partial<Record<CountryKey, SourceDetails>>;
  sourceStatus?: Record<string, SourceStatus>;
};
export type SourceDetails = {
  country: string;
  agency: string;
  dataset: string;
  seriesId: string;
  definition: string;
  unit: string;
  sourceUrl: string;
  reuse: string;
  frequency?: string;
};
export type SourceStatus = {
  status: "current" | "stale" | "held" | "failed" | "local-only";
  message?: string;
  lastSuccessAt?: string | null;
  latestObservation?: string | null;
};

export const BOND_COUNTRIES: Array<{
  key: CountryKey;
  name: string;
  color: string;
  definition: string;
  agency: string;
  sourceUrl: string;
  status: "hosted" | "local-only";
  rightsNote: string;
}> = [
  { key: "US", name: "United States", color: "#533620", definition: "10-year par yield from the Treasury's estimated daily par curve.", agency: "U.S. Department of the Treasury", sourceUrl: "https://home.treasury.gov/resource-center/data-chart-center/interest-rates", status: "hosted", rightsNote: "Numeric government publication hosted with attribution; this records the U.S. federal-government basis and does not claim a universal worldwide open-data licence." },
  { key: "UK", name: "United Kingdom", color: "#da8738", definition: "10-year nominal par yield from the Bank of England's fitted gilt curve.", agency: "Bank of England", sourceUrl: "https://www.bankofengland.co.uk/statistics/yield-curves", status: "hosted", rightsNote: "Open Government Licence terms apply subject to stated exclusions and third-party rights; credit the Bank of England." },
  { key: "France", name: "France", color: "#203e5c", definition: "TEC10 constant-maturity index, calculated by Euronext using MTS France data.", agency: "Banque de France Webstat / Euronext", sourceUrl: "https://webstat.banque-france.fr/en/catalog/fm/FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA", status: "local-only", rightsNote: "Operator-selected personal-interview purpose records intended use only. Euronext terms apply; written permission for this owner-only chart has not been verified. This is not a rights determination." },
  { key: "Italy", name: "Italy", color: "#55a6b9", definition: "Gross yield to maturity on the 10-year benchmark BTP; upstream providers are not itemized.", agency: "Banca d'Italia", sourceUrl: "https://www.bancaditalia.it/statistiche/tematiche/moneta-intermediari-finanza/mercati/index.html", status: "local-only", rightsNote: "Operator-selected personal-interview purpose records intended use only. Banca d'Italia terms apply; written permission has not been verified. BIVA upstream vendors are unspecified; no claim is made that Bloomberg is absent." },
  { key: "Germany", name: "Germany", color: "#2d7953", definition: "Svensson term-structure yield at 10 years residual maturity.", agency: "Deutsche Bundesbank", sourceUrl: "https://www.bundesbank.de/en/statistics/money-and-capital-markets/securities-issues/no-05-yields-and-indices-on-german-securities", status: "hosted", rightsNote: "Bundesbank permits unchanged reproduction with attribution: Source: Deutsche Bundesbank." },
  { key: "Japan", name: "Japan", color: "#242424", definition: "10-year semiannual-compound constant-maturity JGB rate.", agency: "Ministry of Finance Japan", sourceUrl: "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm", status: "hosted", rightsNote: "Public Data License Version 1.0 applies unless otherwise indicated; cite MOF and identify changes." },
];

export const BOND_SOURCE_DETAILS: Record<CountryKey, SourceDetails> = {
  US: { country: "United States", agency: "U.S. Department of the Treasury", dataset: "Daily Treasury Par Yield Curve Rates, 10 Yr", seriesId: "10 Yr column", definition: BOND_COUNTRIES[0].definition, unit: "Percent per annum", sourceUrl: BOND_COUNTRIES[0].sourceUrl, reuse: BOND_COUNTRIES[0].rightsNote },
  UK: { country: "United Kingdom", agency: "Bank of England", dataset: "IUDMNPY — 10 year Nominal Par Yield", seriesId: "IUDMNPY", definition: BOND_COUNTRIES[1].definition, unit: "Percent per annum", sourceUrl: BOND_COUNTRIES[1].sourceUrl, reuse: BOND_COUNTRIES[1].rightsNote },
  France: { country: "France", agency: "Banque de France Webstat / Euronext", dataset: "TEC10 constant maturity", seriesId: "FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA", definition: BOND_COUNTRIES[2].definition, unit: "Percent", sourceUrl: BOND_COUNTRIES[2].sourceUrl, reuse: BOND_COUNTRIES[2].rightsNote },
  Italy: { country: "Italy", agency: "Banca d'Italia", dataset: "BMK0200 daily 10-year benchmark BTP", seriesId: "MFN_BMK.D.020.922.0.EUR.210", definition: BOND_COUNTRIES[3].definition, unit: "Percent", sourceUrl: BOND_COUNTRIES[3].sourceUrl, reuse: BOND_COUNTRIES[3].rightsNote },
  Germany: { country: "Germany", agency: "Deutsche Bundesbank", dataset: "Term-structure yields, 10.0 years residual maturity", seriesId: "BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", definition: BOND_COUNTRIES[4].definition, unit: "Percent", sourceUrl: BOND_COUNTRIES[4].sourceUrl, reuse: BOND_COUNTRIES[4].rightsNote },
  Japan: { country: "Japan", agency: "Ministry of Finance Japan", dataset: "Daily Interest Rate table, 10Y", seriesId: "MOF Interest Rate table, 10Y", definition: BOND_COUNTRIES[5].definition, unit: "Percent", sourceUrl: BOND_COUNTRIES[5].sourceUrl, reuse: BOND_COUNTRIES[5].rightsNote },
};

export function isCountryKey(value: string): value is CountryKey {
  return BOND_COUNTRIES.some((country) => country.key === value);
}
