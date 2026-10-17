from __future__ import annotations
import subprocess, sys, typer
from _bootstrap import ROOT

def run(name,args=[]): subprocess.run([sys.executable,str(ROOT/"scripts"/name),*args],cwd=ROOT,check=True)
def main(years:int=3,stock_code:str|None=None,industry:str|None=None,max_companies:int|None=None,skip_download:bool=False,force_ocr:bool=False,headed:bool=False,source_priority:str="hkex_title_search,hkex_playwright,browser_use,firecrawl,manual",no_llm:bool=True,export_web_data:bool=True):
    filt=[]
    if stock_code: filt += ["--stock-code",stock_code]
    if industry: filt += ["--industry",industry]
    if max_companies: filt += ["--max-companies",str(max_companies)]
    run("01_build_universe.py",filt)
    if not skip_download: run("02_hkex_search_download.py",["--years",str(years),"--source-priority",source_priority,*filt] + (["--headed"] if headed else []))
    run("03_pdf_to_markdown.py",(["--stock-code",stock_code] if stock_code else []) + (["--force-ocr"] if force_ocr else []))
    run("04_extract_metrics.py",["--stock-code",stock_code] if stock_code else [])
    run("05_score_domestic_demand.py",["--stock-code",stock_code] if stock_code else [])
    run("06_generate_report.py",["--export-web-data"] if export_web_data else [])
    run("10_generate_architecture_docs.py")
    typer.echo("Pipeline completed")
if __name__=="__main__": typer.run(main)
