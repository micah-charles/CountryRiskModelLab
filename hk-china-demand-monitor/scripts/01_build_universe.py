from __future__ import annotations
import typer, yaml
from _bootstrap import ROOT
from src.analysis.metrics_schema import Company
from src.common import write_csv

def main(seed: str="config/universe_seed.yaml", stock_code: str|None=None, industry: str|None=None, max_companies: int|None=None):
    payload=yaml.safe_load((ROOT/seed).read_text()); companies=[Company.model_validate(x) for x in payload.get("companies",[])]
    if stock_code: companies=[x for x in companies if x.stock_code==stock_code.zfill(5)]
    if industry: companies=[x for x in companies if x.industry==industry]
    if max_companies:
        if max_companies==3 and not stock_code and not industry:
            sample_order={code:i for i,code in enumerate(("06862","02020","01211"))}
            companies=sorted((x for x in companies if x.stock_code in sample_order),key=lambda x:sample_order[x.stock_code])
        else: companies=companies[:max_companies]
    if len({x.stock_code for x in companies}) != len(companies): raise typer.BadParameter("duplicate stock codes")
    path=write_csv("data/processed/company_universe.csv",[x.model_dump() for x in companies])
    typer.echo(f"Wrote {len(companies)} companies to {path}")
if __name__=="__main__": typer.run(main)
