from __future__ import annotations
import json, os, subprocess, time, typer
from _bootstrap import ROOT
from src.common import now_iso, read_csv, write_csv, sha256_text
from src.hkex import download_pdf, manual_candidates, discover_hkex_reports
from src.hkex.metadata import normalize_title, canonical_url

FIELDS=["document_id","stock_code","stock_short_name","company_name","industry","document_title","release_date","financial_year","hkex_url","pdf_url","source_method","source_page_url","discovered_pdf_url","crawl_timestamp","confidence_score","reason_for_match","file_size","sha256","local_pdf_path","download_status","error_message"]

def main(years:int=3, stock_code:str|None=None, industry:str|None=None, manual_links:str="config/manual_report_links.csv", headed:bool=False, max_companies:int|None=None, source_priority:str="hkex_title_search,hkex_playwright,browser_use,firecrawl,manual", enable_firecrawl:bool=False, dry_run:bool=False, force:bool=False):
    universe=read_csv("data/processed/company_universe.csv")
    if stock_code: universe=[x for x in universe if x["stock_code"]==stock_code.zfill(5)]
    if industry: universe=[x for x in universe if x["industry"]==industry]
    if max_companies: universe=universe[:max_companies]
    codes=[x["stock_code"] for x in universe]; by_code={x["stock_code"]:x for x in universe}; candidates=[]
    if "hkex_title_search" in source_priority:
        official,failures=discover_hkex_reports(codes,years=years,delay=1.5); candidates.extend(official)
        if failures:
            (ROOT/"logs").mkdir(exist_ok=True); (ROOT/"logs/hkex_title_search_failures.json").write_text(json.dumps(failures,indent=2))
        typer.echo(f"Official HKEX title search discovered {len(official)} reports; {len(failures)} issuer failures")
    discovered=ROOT/"data/interim/hkex_discovered.json"
    covered={c["stock_code"] for c in candidates}; browser_codes=[code for code in codes if code not in covered]
    if "hkex_playwright" in source_priority and browser_codes and not dry_run:
        cmd=["npx","tsx","browser/hkex_download_playwright.ts","--codes",",".join(browser_codes),"--years",str(years),"--output",str(discovered)]
        if headed: cmd.append("--headed")
        try: subprocess.run(cmd,cwd=ROOT,check=False,timeout=max(90,len(codes)*45))
        except (FileNotFoundError,subprocess.TimeoutExpired) as exc: typer.echo(f"Playwright unavailable: {exc}")
    if "hkex_playwright" in source_priority and discovered.exists():
        try: candidates.extend(json.loads(discovered.read_text()))
        except json.JSONDecodeError: pass
    candidates.extend(manual_candidates(manual_links,codes))
    priority={name:i for i,name in enumerate(source_priority.split(","))}; best={}
    for c in candidates:
        key=(str(c.get("stock_code","")).zfill(5),str(c.get("financial_year") or "0")); current=best.get(key)
        if current is None or priority.get(c.get("source_method","manual"),99)<priority.get(current.get("source_method","manual"),99): best[key]=c
    existing=read_csv("data/processed/document_inventory.csv"); indexed={(r.get("stock_code"),str(r.get("financial_year"))):r for r in existing}
    for c in best.values():
        code=str(c.get("stock_code","")).zfill(5); company=by_code.get(code,{})
        year=int(c.get("financial_year") or 0); url=c.get("pdf_url") or c.get("discovered_pdf_url","")
        key=(code,str(year)); old=indexed.get(key)
        if force and old and canonical_url(old.get("pdf_url",""))==canonical_url(url) and old.get("download_status") in ("downloaded","cached"): continue
        if not force and old and old.get("download_status") in ("downloaded","cached") and "hkexnews.hk" in old.get("pdf_url",""): continue
        if not force and old and priority.get(old.get("source_method","manual"),99)<=priority.get(c.get("source_method","manual"),99) and old.get("download_status") in ("downloaded","cached"): continue
        rel=f"data/raw/annual_reports/{code}/{year}/{code}_{year}_annual_report.pdf"
        destination=ROOT/rel
        if force and old and destination.exists():
            archive=destination.with_name(f"{destination.stem}_excluded_{old.get('sha256','unknown')[:12]}{destination.suffix}")
            if not archive.exists(): destination.replace(archive)
        result={"status":"dry_run","file_size":0,"sha256":""} if dry_run else download_pdf(url,rel)
        title=c.get("document_title") or c.get("title") or f"Annual Report {year}"
        doc_hash=result.get("sha256") or sha256_text(url)[:24]
        row={"document_id":f"{code}:{year}:{normalize_title(title)}:{doc_hash}","stock_code":code,"stock_short_name":company.get("name_en",c.get("company_name","")),"company_name":company.get("name_en",c.get("company_name","")),"industry":company.get("industry",c.get("industry","")),"document_title":title,"release_date":c.get("release_date",""),"financial_year":year,"hkex_url":c.get("hkex_url") or c.get("source_page_url", ""),"pdf_url":url,"source_method":c.get("source_method","manual"),"source_page_url":c.get("source_page_url",""),"discovered_pdf_url":url,"crawl_timestamp":c.get("crawl_timestamp",now_iso()),"confidence_score":c.get("confidence_score",1),"reason_for_match":c.get("reason_for_match","annual-report title match"),"file_size":result.get("file_size",0),"sha256":result.get("sha256",""),"local_pdf_path":rel,"download_status":result.get("status"),"error_message":result.get("error_message","")}
        indexed[key]=row
        if not dry_run: time.sleep(float(os.getenv("HKEX_DELAY_SECONDS","1")))
    rows=list(indexed.values()); write_csv("data/processed/document_inventory.csv",rows,FIELDS); typer.echo(f"Inventory contains {len(rows)} reports ({len(candidates)} candidates this run)")
if __name__=="__main__": typer.run(main)
