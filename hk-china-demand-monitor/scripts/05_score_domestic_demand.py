from __future__ import annotations
import json, typer, yaml
from _bootstrap import ROOT
from src.common import read_csv, write_csv, write_json
from src.analysis.scorer import score_row
from src.analysis.industry_rollup import rollup

def main(stock_code:str|None=None):
    rows=read_csv("data/processed/company_year_metrics.csv"); cfg=yaml.safe_load((ROOT/"config/scoring_weights.yaml").read_text()); weights=cfg["weights"]
    scores=[] if not stock_code else [x for x in read_csv("data/processed/demand_pressure_scores.csv") if x["stock_code"]!=stock_code.zfill(5)]
    groups={}
    for r in rows: groups.setdefault(r["stock_code"],[]).append(r)
    for code,items in groups.items():
        if stock_code and code != stock_code.zfill(5): continue
        items.sort(key=lambda x:int(x["financial_year"])); previous=None
        for row in items:
            score,confidence,components=score_row(row,previous,weights)
            scores.append({"stock_code":code,"company_name":row["company_name"],"industry":row["industry"],"financial_year":int(row["financial_year"]),"demand_pressure_score":score,"confidence":confidence,"score_status":"verified" if score is not None and confidence>=.5 else ("needs_review" if score is not None else "missing"),"components_json":json.dumps(components,sort_keys=True)}); previous=row
    industries=rollup(scores); write_csv("data/processed/demand_pressure_scores.csv",scores); write_json("data/processed/demand_pressure_scores.json",scores); write_csv("data/processed/industry_summary.csv",industries); write_json("data/processed/industry_summary.json",industries); typer.echo(f"Scored {len(scores)} company-years and {len(industries)} industry-years")
if __name__=="__main__": typer.run(main)
