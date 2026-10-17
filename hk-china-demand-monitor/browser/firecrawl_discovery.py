from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.common import now_iso

def main():
    p=argparse.ArgumentParser(); p.add_argument("--stock-code",required=True); p.add_argument("--years",type=int,default=3); p.add_argument("--url",default="https://www1.hkexnews.hk/search/titlesearch.xhtml"); a=p.parse_args()
    api=os.getenv("FIRECRAWL_API_URL","http://localhost:3002").rstrip("/"); headers={"Content-Type":"application/json"}; key=os.getenv("FIRECRAWL_API_KEY");
    if key: headers["Authorization"]=f"Bearer {key}"
    response=requests.post(f"{api}/v1/scrape",headers=headers,json={"url":a.url,"formats":["markdown","html"]},timeout=120); response.raise_for_status(); payload=response.json(); data=payload.get("data",payload); md=data.get("markdown",""); html=data.get("html","")
    links=sorted(set(re.findall(r"https?://[^\s\)\]\"']+\.pdf(?:\?[^\s\)\]\"']*)?",md+"\n"+html,re.I))); candidates=[x for x in links if re.search(r"annual|年報|年度",x,re.I)]
    out=ROOT/f"data/interim/firecrawl/{a.stock_code}/unknown"; out.mkdir(parents=True,exist_ok=True); (out/"page.md").write_text(md); (out/"page.html").write_text(html); (out/"crawl_result.json").write_text(json.dumps({"stock_code":a.stock_code,"source_page_url":a.url,"crawl_timestamp":now_iso(),"candidate_pdf_urls":candidates,"needs_manual_review":not bool(candidates)},indent=2)); print(json.dumps(candidates,indent=2))
if __name__=="__main__": main()

