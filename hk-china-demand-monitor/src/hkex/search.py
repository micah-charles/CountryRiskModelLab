"""Official HKEX title-search discovery plus analyst-supplied fallback."""
from __future__ import annotations
import re, time
from datetime import date
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from src.common import read_csv, now_iso
from src.hkex.metadata import is_annual_report

ACTIVE_STOCK_URL="https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"
TITLE_SEARCH_URL="https://www1.hkexnews.hk/search/titlesearch.xhtml"
HEADERS={"User-Agent":"hk-china-demand-monitor/0.1 research; cache-first (+official HKEX title search)"}

def active_stock_catalog(session=None):
    s=session or requests.Session(); response=s.get(ACTIVE_STOCK_URL,headers=HEADERS,timeout=45); response.raise_for_status()
    return response.json()

def resolve_stock_ids(stock_codes, session=None):
    wanted={str(x).zfill(5) for x in stock_codes}; result={}
    for item in active_stock_catalog(session):
        code=str(item.get("c","")).zfill(5)
        if code in wanted and code not in result: result[code]={"stock_id":str(item["i"]),"stock_short_name":item.get("n","")}
    return result

def _financial_year(title, release_date):
    patterns=(r"(?:annual report|年度報告|年報)\s*(20\d{2})",r"(20\d{2})\s*(?:annual report|年度報告|年報)")
    for pattern in patterns:
        match=re.search(pattern,title,re.I)
        if match: return int(match.group(1))
    match=re.search(r"\d{1,2}/\d{1,2}/(20\d{2})",release_date)
    return int(match.group(1))-1 if match else 0

def discover_hkex_reports(stock_codes, years=3, delay=1.5, session=None):
    s=session or requests.Session(); ids=resolve_stock_ids(stock_codes,s); today=date.today(); start=date(today.year-years-2,1,1); candidates=[]; failures=[]
    for index,code in enumerate(stock_codes):
        meta=ids.get(str(code).zfill(5))
        if not meta:
            failures.append({"stock_code":code,"error":"stock code absent from active HKEX catalogue"}); continue
        data={"lang":"EN","category":"0","market":"SEHK","searchType":"rbAll","documentType":"","t1code":"","t2Gcode":"","t2code":"","stockId":meta["stock_id"],"from":start.strftime("%Y%m%d"),"to":today.strftime("%Y%m%d"),"title":"Annual Report"}
        try:
            response=s.post(TITLE_SEARCH_URL,data=data,headers=HEADERS,timeout=60); response.raise_for_status(); soup=BeautifulSoup(response.text,"lxml"); found=[]
            for row in soup.select("#titleSearchResultPanel tbody tr"):
                row_text=" ".join(row.get_text(" ",strip=True).split()); link=None
                for anchor in row.select("a[href]"):
                    if str(anchor.get("href","")).lower().split("?")[0].endswith(".pdf"): link=anchor; break
                if not link: continue
                title=" ".join(link.get_text(" ",strip=True).split())
                if not is_annual_report(title) or re.search(r"environmental|sustainability|esg|notification|request form|notice of publication|letter to|circular|supplemental|clarification|voluntary announcement|despatch|report of the board|profit distribution|annual general meeting|audited consolidated",title,re.I): continue
                released=(re.search(r"Release Time:\s*([^|]+?)\s*Stock Code:",row_text) or re.search(r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})",row_text))
                release_date=released.group(1).strip() if released else ""; year=_financial_year(title,release_date)
                if not year: continue
                pdf_url=urljoin("https://www1.hkexnews.hk",link["href"]); source=f"{TITLE_SEARCH_URL}?category=0&market=SEHK&stockId={meta['stock_id']}"
                found.append({"stock_code":str(code).zfill(5),"stock_short_name":meta["stock_short_name"],"financial_year":year,"document_title":title,"release_date":release_date,"pdf_url":pdf_url,"hkex_url":source,"source_method":"hkex_title_search","source_page_url":source,"discovered_pdf_url":pdf_url,"crawl_timestamp":now_iso(),"confidence_score":.98,"reason_for_match":"Official HKEX title-search result matched Annual Report and financial year"})
            seen=set()
            for item in sorted(found,key=lambda x:x["financial_year"],reverse=True):
                if item["financial_year"] in seen: continue
                seen.add(item["financial_year"]); candidates.append(item)
                if len(seen)>=years: break
            if not found: failures.append({"stock_code":code,"error":"no Annual Report rows returned by HKEX title search"})
        except Exception as exc: failures.append({"stock_code":code,"error":str(exc)})
        if index+1<len(stock_codes): time.sleep(delay)
    return candidates, failures

def manual_candidates(path="config/manual_report_links.csv", stock_codes=None):
    wanted = {str(x).zfill(5) for x in stock_codes or []}
    rows = read_csv(path)
    return [dict(r, stock_code=str(r["stock_code"]).zfill(5), source_method="manual", source_page_url=r.get("hkex_url", ""), discovered_pdf_url=r.get("pdf_url", ""), confidence_score=1.0, reason_for_match="analyst-supplied") for r in rows if not wanted or str(r["stock_code"]).zfill(5) in wanted]
