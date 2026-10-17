from __future__ import annotations
import subprocess, sys, uuid, typer
from _bootstrap import ROOT
from src.common import read_csv, write_csv, write_json, now_iso, sha256_file, sha256_text, relative
from src.state.store import StateStore, classify_change, should_reprocess
from src.hkex.metadata import normalize_title

def call(script,args=[]): subprocess.run([sys.executable,str(ROOT/"scripts"/script),*args],cwd=ROOT,check=True)

def main(years:int=3,stock_code:str|None=None,industry:str|None=None,since:str|None=None,force:bool=False,dry_run:bool=False,no_llm:bool=True,export_web_data:bool=False,max_new_documents:int=20,source_priority:str="hkex_title_search,hkex_playwright,browser_use,firecrawl,manual"):
    started=now_iso(); run_id=str(uuid.uuid4()); store=StateStore(); changes=[]
    filt=[]
    if stock_code: filt += ["--stock-code",stock_code]
    if industry: filt += ["--industry",industry]
    # Discovery is deliberately skipped in dry-run because that mode must not mutate files.
    if not dry_run: call("02_hkex_search_download.py",["--years",str(years),"--source-priority",source_priority,*filt])
    inventory=read_csv("data/processed/document_inventory.csv")
    if stock_code: inventory=[x for x in inventory if x["stock_code"]==stock_code.zfill(5)]
    if industry: inventory=[x for x in inventory if x["industry"]==industry]
    for doc in inventory:
        pdf=ROOT/doc["local_pdf_path"]; sha=sha256_file(pdf) if pdf.exists() else doc.get("sha256","")
        md=ROOT/f"data/interim/markdown/{doc['stock_code']}/{doc['financial_year']}/annual_report.md"; content=sha256_text(md.read_text(errors="replace")) if md.exists() else ""
        doc_id=doc.get("document_id") or f"{doc['stock_code']}:{doc['financial_year']}:{normalize_title(doc['document_title'])}:{sha or sha256_text(doc.get('pdf_url',''))[:24]}"
        old=store.get_document(doc_id); kind=classify_change(old,sha,content,force)
        changes.append({"doc":doc,"document_id":doc_id,"sha":sha,"content":content,"old":old,"change_type":kind})
    # A first state bootstrap must not repeat expensive work when complete outputs already exist.
    selected=[x for x in changes if should_reprocess(x["change_type"],x["old"] is not None,(ROOT/f"data/interim/markdown/{x['doc']['stock_code']}/{x['doc']['financial_year']}/annual_report.md").exists(),force)][:max_new_documents]
    selected_ids={x["document_id"] for x in selected}
    if dry_run:
        for x in changes: typer.echo(f"{x['change_type']}: {x['doc']['stock_code']} FY{x['doc']['financial_year']}")
        store.close(); return
    affected=sorted({x["doc"]["stock_code"] for x in selected})
    for code in affected:
        code_items=[x for x in selected if x["doc"]["stock_code"]==code]
        pdf_changed=any(x["old"] is None or x["old"].get("sha256")!=x["sha"] or force for x in code_items)
        if pdf_changed: call("03_pdf_to_markdown.py",["--stock-code",code])
        call("04_extract_metrics.py",["--stock-code",code]); call("05_score_domestic_demand.py",["--stock-code",code])
    log=[]
    for x in changes:
        doc=x["doc"]; md=ROOT/f"data/interim/markdown/{doc['stock_code']}/{doc['financial_year']}/annual_report.md"; current_content=sha256_text(md.read_text(errors="replace")) if md.exists() else x["content"]
        store.upsert_document({"document_id":x["document_id"],"stock_code":doc["stock_code"],"company_name":doc["company_name"],"industry":doc["industry"],"financial_year":int(doc["financial_year"]),"report_title":doc["document_title"],"source_method":doc.get("source_method",""),"hkex_result_page_url":doc.get("hkex_url",""),"source_document_url":doc.get("pdf_url",""),"local_pdf_path":doc["local_pdf_path"],"release_date":doc.get("release_date",""),"file_size":int(doc.get("file_size") or 0),"sha256":x["sha"],"content_hash":current_content,"page_count":0,"last_processed_at":now_iso() if x["change_type"]!="unchanged" else (x["old"] or {}).get("last_processed_at",""),"status":"processed" if x["sha"] else "missing"})
        was_selected=x["document_id"] in selected_ids
        log.append({"run_id":run_id,"run_timestamp":started,"stock_code":doc["stock_code"],"financial_year":doc["financial_year"],"change_type":x["change_type"],"previous_sha256":(x["old"] or {}).get("sha256",""),"new_sha256":x["sha"],"steps_reprocessed":"pdf,metrics,scores" if was_selected else "","steps_skipped":"all" if x["change_type"]=="unchanged" else ("reused_existing_outputs" if not was_selected else ""),"web_files_updated":bool(export_web_data and was_selected),"llm_cache_hits":0,"llm_cache_misses":0,"status":"ok","error_message":""})
    counts={k:sum(x["change_type"]==k for x in changes) for k in ("new","changed","unchanged")}; finished=now_iso()
    run={"run_id":run_id,"run_type":"incremental","started_at":started,"finished_at":finished,"status":"success","discovered_count":len(changes),"new_count":counts["new"],"changed_count":counts["changed"],"skipped_count":counts["unchanged"],"failed_count":0,"notes":f"affected={affected}"}; store.add_run(run); store.close()
    write_csv("data/processed/incremental_update_log.csv",log); write_json("state/run_manifest.json",run); write_json("state/last_successful_run.json",run); write_json("state/content_hash_index.json",{x["document_id"]:x["content"] for x in changes})
    if affected: call("06_generate_report.py",["--export-web-data"] if export_web_data else [])
    typer.echo(f"Incremental run: {counts}; affected companies: {affected}")
if __name__=="__main__": typer.run(main)
