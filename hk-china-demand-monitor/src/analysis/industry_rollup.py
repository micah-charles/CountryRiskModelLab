from __future__ import annotations
from collections import defaultdict
def rollup(scores):
    groups=defaultdict(list)
    for row in scores:
        if row.get("demand_pressure_score") not in (None,""): groups[(row["industry"],row["financial_year"])].append(float(row["demand_pressure_score"]))
    return [{"industry":k[0],"financial_year":k[1],"demand_pressure_score":round(sum(v)/len(v),2),"company_count":len(v)} for k,v in sorted(groups.items())]

