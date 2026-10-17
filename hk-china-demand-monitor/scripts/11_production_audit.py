from __future__ import annotations
import json, sqlite3, typer, yaml
from collections import Counter, defaultdict
from _bootstrap import ROOT
from src.common import read_csv, sha256_file, write_json, now_iso

def main(expected_years:int=3):
    checks=[]
    def check(name,ok,detail): checks.append({"check":name,"status":"pass" if ok else "fail","detail":detail})
    universe=read_csv("data/processed/company_universe.csv"); inventory=read_csv("data/processed/document_inventory.csv"); sources=read_csv("data/processed/source_documents.csv"); pages=read_csv("data/processed/source_page_index.csv"); metrics=read_csv("data/processed/company_year_metrics.csv"); evidence=read_csv("data/processed/metric_evidence.csv"); scores=read_csv("data/processed/demand_pressure_scores.csv"); quality=read_csv("data/processed/extraction_quality_log.csv")
    codes={x["stock_code"] for x in universe}; grouped=defaultdict(list)
    for x in inventory: grouped[x["stock_code"]].append(x)
    check("seed_universe",len(universe)>=26 and len(codes)==len(universe),f"{len(universe)} unique companies")
    check("three_year_document_coverage",set(grouped)==codes and all(len(v)==expected_years for v in grouped.values()),f"coverage distribution {dict(Counter(len(v) for v in grouped.values()))}")
    bad_files=[]
    for d in inventory:
        path=ROOT/d["local_pdf_path"]
        if d.get("download_status") not in ("downloaded","cached") or not path.exists() or path.stat().st_size<1000 or path.read_bytes()[:4]!=b"%PDF" or (d.get("sha256") and sha256_file(path)!=d["sha256"]): bad_files.append(f"{d['stock_code']}:{d['financial_year']}")
    check("pdf_integrity",not bad_files,f"{len(inventory)-len(bad_files)}/{len(inventory)} PDFs pass status, header, size, and SHA-256; bad={bad_files[:10]}")
    check("source_document_lineage",len(sources)==len(inventory) and all(x.get("source_document_url") and x.get("local_pdf_path") and x.get("sha256") for x in sources),f"{len(sources)} source rows")
    page_expected=sum(int(x["page_count"]) for x in sources); check("page_index",len(pages)==page_expected and all(x.get("local_markdown_path") and x.get("pdf_page") for x in pages),f"{len(pages)} indexed pages; expected {page_expected}")
    markdown_bad=[]
    for d in inventory:
        path=ROOT/f"data/interim/markdown/{d['stock_code']}/{d['financial_year']}/annual_report.md"; text=path.read_text(errors="replace") if path.exists() else ""
        if not text.startswith("---") or "<!-- page: 1 -->" not in text: markdown_bad.append(f"{d['stock_code']}:{d['financial_year']}")
    check("markdown_contract",not markdown_bad,f"{len(inventory)-len(markdown_bad)}/{len(inventory)} Markdown reports have front matter and page markers")
    keys={(x["stock_code"],x["financial_year"]) for x in inventory}; metric_keys={(x["stock_code"],x["financial_year"]) for x in metrics}; check("company_year_metrics",metric_keys==keys and len(metrics)==len(inventory),f"{len(metrics)} company-year rows")
    schema=yaml.safe_load((ROOT/"config/extraction_schema.yaml").read_text()); expected_evidence=len(inventory)*(len(schema["metrics"])+1)
    invalid_evidence=[x for x in evidence if not ((x.get("evidence_text") and x.get("pdf_page") and x.get("source_document_url")) or x.get("missing_reason"))]
    check("evidence_contract",len(evidence)==expected_evidence and not invalid_evidence,f"{len(evidence)}/{expected_evidence} rows; invalid={len(invalid_evidence)}")
    score_bad=[x for x in scores if x.get("demand_pressure_score") not in (None,"") and not 0<=float(x["demand_pressure_score"])<=5]; check("score_bounds",len(scores)==len(inventory) and not score_bad,f"{len(scores)} score rows; out of range={len(score_bad)}")
    check("quality_log",len(quality)==len(inventory) and all(x.get("quality_score") for x in quality),f"{len(quality)} quality rows; {sum(x.get('needs_manual_review')=='True' for x in quality)} flagged")
    db=sqlite3.connect(ROOT/"state/document_state.sqlite"); state_count=db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]; db.close(); check("incremental_state",state_count==len(inventory),f"{state_count} state documents")
    required_web=["company_universe.json","document_inventory.json","company_year_metrics.json","demand_pressure_scores.json","industry_summary.json","metric_evidence.json","source_documents.json","source_page_index.json","quality_warnings.json","latest_run.json"]; missing_web=[x for x in required_web if not (ROOT/"web/public/data"/x).exists()]; check("web_exports",not missing_web,f"missing={missing_web}")
    result={"audited_at":now_iso(),"status":"pass" if all(x["status"]=="pass" for x in checks) else "fail","checks":checks,"summary":{"companies":len(universe),"documents":len(inventory),"pages":len(pages),"metric_rows":len(metrics),"evidence_rows":len(evidence),"usable_scores":sum(bool(x.get("demand_pressure_score")) for x in scores)}}; write_json("data/processed/production_audit.json",result)
    md=["# Production Dataset Audit","",f"Status: **{result['status'].upper()}**",f"Audited: `{result['audited_at']}`","","| Check | Status | Evidence |","|---|---|---|"]+[f"| {x['check']} | {x['status']} | {x['detail']} |" for x in checks]; (ROOT/"docs/PRODUCTION_DATASET_AUDIT.md").write_text("\n".join(md)+"\n")
    for x in checks: typer.echo(f"{x['status'].upper():4} {x['check']}: {x['detail']}")
    if result["status"]!="pass": raise typer.Exit(1)
if __name__=="__main__": typer.run(main)

