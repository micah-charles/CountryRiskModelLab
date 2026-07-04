export const REGRESSION_DEPENDENT_PREFERENCES = ["bond_yield_10y", "gdp_growth_yoy", "inflation_yoy"];
export const REGRESSION_INDEPENDENT_PREFERENCES = [
  "inflation_yoy",
  "policy_rate",
  "debt_gdp",
  "current_account_gdp",
  "global_risk_index",
  "fiscal_balance_gdp",
  "unemployment_rate",
];
export const FORECAST_TARGET_PREFERENCES = ["bond_yield_10y", "gdp_growth_yoy", "inflation_yoy"];
export const FORECAST_EXTERNAL_PREFERENCES = ["policy_rate", "inflation_yoy", "global_risk_index", "debt_gdp", "current_account_gdp"];
export const VAR_VARIABLE_PREFERENCES = [
  "inflation_yoy",
  "policy_rate",
  "bond_yield_10y",
  "fx_depreciation_yoy",
  "gdp_growth_yoy",
  "debt_gdp",
  "current_account_gdp",
  "fiscal_balance_gdp",
];

export function pickCountry(countries: string[], current: string): string {
  return countries.includes(current) ? current : countries[0] || "";
}

export function pickFirstAvailable(values: string[], preferred: string[]): string {
  return preferred.find((item) => values.includes(item)) || values[0] || "";
}

export function pickManyAvailable(values: string[], preferred: string[], exclude: string[] = [], limit?: number): string[] {
  const excluded = new Set(exclude);
  const picked: string[] = [];
  for (const item of preferred) {
    if (values.includes(item) && !excluded.has(item) && !picked.includes(item)) {
      picked.push(item);
    }
  }
  for (const item of values) {
    if (!excluded.has(item) && !picked.includes(item)) {
      picked.push(item);
    }
  }
  return typeof limit === "number" ? picked.slice(0, limit) : picked;
}

export function keepValidSelection(selected: string[], values: string[]): string[] {
  return selected.filter((item) => values.includes(item));
}
