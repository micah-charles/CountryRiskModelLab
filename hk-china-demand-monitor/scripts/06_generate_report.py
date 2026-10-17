from __future__ import annotations
import json, shutil, typer
from _bootstrap import ROOT
from src.common import read_csv, read_json, write_json, now_iso
from src.reporting.render_markdown import render, html_from_markdown

def export_web_data():
    dest=ROOT/"web/public/data"; dest.mkdir(parents=True,exist_ok=True)
    mappings={"company_universe.csv":"company_universe.json","document_inventory.csv":"document_inventory.json","company_year_metrics.csv":"company_year_metrics.json","demand_pressure_scores.csv":"demand_pressure_scores.json","industry_summary.csv":"industry_summary.json","metric_evidence.csv":"metric_evidence.json","source_documents.csv":"source_documents.json","source_page_index.csv":"source_page_index.json","extraction_quality_log.csv":"quality_warnings.json"}
    for src,name in mappings.items(): write_json(dest/name,read_csv("data/processed/"+src))
    write_json(dest/"latest_run.json",{"exported_at":now_iso()})

def main(export_web_data_flag:bool=typer.Option(False,"--export-web-data")):
    values=[read_csv(f"data/processed/{x}") for x in ("company_universe.csv","document_inventory.csv","extraction_quality_log.csv","company_year_metrics.csv","demand_pressure_scores.csv","industry_summary.csv","metric_evidence.csv")]
    md=render(*values,run_meta=read_json("state/last_successful_run.json",{})); out=ROOT/"data/reports/china_domestic_demand_summary.md"; out.write_text(md); (out.with_suffix(".html")).write_text(html_from_markdown(md))
    if export_web_data_flag: export_web_data()
    typer.echo(f"Wrote {out} and HTML" + ("; exported web data" if export_web_data_flag else ""))
if __name__=="__main__": typer.run(main)

