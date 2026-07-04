from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


COUNTRIES = ["Indonesia", "Brazil", "South Africa", "Turkey", "Mexico", "India"]
DATA_DIR = Path(__file__).resolve().parent / "data"


def make_quarterly() -> pd.DataFrame:
    rng = np.random.default_rng(20260703)
    dates = [f"{year}-Q{quarter}" for year in range(2015, 2026) for quarter in range(1, 5)]
    rows = []
    country_offsets = {
        "Indonesia": (5.1, 3.2, 5.6, 32, -1.8),
        "Brazil": (1.7, 5.5, 8.8, 78, -2.1),
        "South Africa": (1.2, 5.1, 7.1, 68, -2.8),
        "Turkey": (3.8, 12.5, 16.0, 39, -3.4),
        "Mexico": (2.1, 4.2, 6.2, 52, -1.1),
        "India": (6.2, 5.0, 6.0, 84, -1.5),
    }
    for country in COUNTRIES:
        growth_base, inflation_base, rate_base, debt_base, ca_base = country_offsets[country]
        global_risk = 50.0
        fx_index = 100.0
        for i, date in enumerate(dates):
            cycle = np.sin(i / 3.0)
            global_risk = 0.85 * global_risk + 7 + rng.normal(0, 2)
            gdp_growth_yoy = growth_base + 0.7 * cycle - 0.025 * global_risk + rng.normal(0, 0.35)
            inflation_yoy = inflation_base + 0.8 * cycle + 0.035 * global_risk + rng.normal(0, 0.45)
            policy_rate = rate_base + 0.55 * inflation_yoy + rng.normal(0, 0.35)
            debt_gdp = debt_base + 0.08 * i - 0.15 * gdp_growth_yoy + rng.normal(0, 1.2)
            current_account_gdp = ca_base + 0.05 * gdp_growth_yoy - 0.03 * global_risk + rng.normal(0, 0.35)
            fx_depreciation_yoy = 1.2 + 0.18 * inflation_yoy + 0.06 * global_risk - 0.18 * gdp_growth_yoy + rng.normal(0, 1.0)
            fx_index *= 1 + fx_depreciation_yoy / 400
            reserves_months_imports = max(1.8, 7.2 - 0.04 * debt_gdp - 0.12 * fx_depreciation_yoy + rng.normal(0, 0.25))
            bond_yield_10y = (
                1.9
                + 0.24 * inflation_yoy
                + 0.33 * policy_rate
                + 0.025 * debt_gdp
                - 0.26 * current_account_gdp
                + 0.05 * fx_depreciation_yoy
                + 0.018 * global_risk
                + rng.normal(0, 0.45)
            )
            rows.append(
                {
                    "country": country,
                    "date": date,
                    "gdp_growth_yoy": round(gdp_growth_yoy, 3),
                    "inflation_yoy": round(inflation_yoy, 3),
                    "policy_rate": round(policy_rate, 3),
                    "bond_yield_10y": round(bond_yield_10y, 3),
                    "debt_gdp": round(debt_gdp, 3),
                    "current_account_gdp": round(current_account_gdp, 3),
                    "fx_depreciation_yoy": round(fx_depreciation_yoy, 3),
                    "reserves_months_imports": round(reserves_months_imports, 3),
                    "global_risk_index": round(global_risk, 3),
                }
            )
    return pd.DataFrame(rows)


def make_monthly() -> pd.DataFrame:
    rng = np.random.default_rng(20260704)
    dates = [f"{year}-{month:02d}" for year in range(2015, 2026) for month in range(1, 13)]
    rows = []
    bases = {
        "Indonesia": (3.4, 5.8, 6.5),
        "Brazil": (5.8, 9.2, 10.6),
        "South Africa": (5.2, 7.4, 9.1),
        "Turkey": (13.5, 17.5, 18.7),
        "Mexico": (4.5, 6.4, 7.5),
        "India": (5.3, 6.1, 7.0),
    }
    for country in COUNTRIES:
        inflation_base, rate_base, yield_base = bases[country]
        fx_index = 100.0
        global_risk = 48.0
        for i, date in enumerate(dates):
            seasonal = np.sin(i / 6.0)
            global_risk = 0.9 * global_risk + 5 + rng.normal(0, 2.5)
            inflation_yoy = inflation_base + 0.5 * seasonal + 0.025 * global_risk + rng.normal(0, 0.35)
            policy_rate = rate_base + 0.45 * inflation_yoy + rng.normal(0, 0.25)
            fx_depreciation_yoy = 0.8 + 0.16 * inflation_yoy + 0.05 * global_risk + rng.normal(0, 0.9)
            fx_index *= 1 + fx_depreciation_yoy / 1200
            bond_yield_10y = yield_base + 0.22 * inflation_yoy + 0.29 * policy_rate + 0.021 * global_risk + 0.04 * fx_depreciation_yoy + rng.normal(0, 0.35)
            rows.append(
                {
                    "country": country,
                    "date": date,
                    "inflation_yoy": round(inflation_yoy, 3),
                    "policy_rate": round(policy_rate, 3),
                    "bond_yield_10y": round(bond_yield_10y, 3),
                    "fx_index": round(fx_index, 3),
                    "fx_depreciation_yoy": round(fx_depreciation_yoy, 3),
                    "global_risk_index": round(global_risk, 3),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    make_quarterly().to_csv(DATA_DIR / "sample_country_risk_quarterly.csv", index=False)
    make_monthly().to_csv(DATA_DIR / "sample_country_risk_monthly.csv", index=False)


if __name__ == "__main__":
    main()

