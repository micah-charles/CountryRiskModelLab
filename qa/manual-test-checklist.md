# Manual QA Checklist

## IMF Data Connector QA

1. Open IMF Data Connector page.
2. Confirm default countries are shown.
3. Confirm default indicators are shown with descriptions.
4. Click Fetch from IMF API.
5. Confirm progress states appear.
6. Confirm dataset preview appears.
7. Confirm missing value summary appears.
8. Confirm dataset is saved to dataset registry.
9. Click Use in Regression Lab.
10. Confirm IMF dataset is selected in Regression Lab.
11. Run a regression using IMF-fetched indicators.
12. Confirm model result appears.
13. Generate model memo.
14. Confirm memo includes IMF data source and limitations.
15. Disconnect internet or mock API failure.
16. Confirm user-friendly failure message appears.

## General App QA

1. Start backend.
2. Start frontend.
3. Open homepage.
4. Load sample quarterly dataset.
5. Run regression for Indonesia `bond_yield_10y`.
6. Confirm coefficient table appears.
7. Confirm residual chart appears.
8. Confirm Python code appears.
9. Generate model memo.
10. Load monthly dataset.
11. Run ARIMA forecast.
12. Run SARIMAX forecast.
13. Run Auto ARIMA grid search.
14. Open VAR Lab.
15. Run VAR with inflation, policy rate, bond yield, FX depreciation.
16. Confirm helpful error appears if too many variables are selected with short sample.

