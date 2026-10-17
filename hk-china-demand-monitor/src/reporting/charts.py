"""Chart-ready series helpers used by future report renderers."""
def score_series(rows, stock_code):
    return sorted(({"year":int(r["financial_year"]),"score":float(r["demand_pressure_score"])} for r in rows if r.get("stock_code")==stock_code and r.get("demand_pressure_score") not in (None,"")),key=lambda x:x["year"])

