from __future__ import annotations
import json, re, typer, yaml
from _bootstrap import ROOT
from src.common import read_csv, write_csv, write_json
from src.pdf.markdown_cleaner import split_pages
from src.analysis.financial_extractors import find_metric
from src.analysis.narrative_extractors import narrative_signals
from src.analysis.metrics_schema import Evidence

def frontmatter(text):
    m=re.match(r"---\s*\n(.*?)\n---",text,re.S); return yaml.safe_load(m.group(1)) if m else {}

def exclusion_reason(metric, raw, snippet):
    text=snippet.lower(); raw_lower=raw.lower()
    if metric=="revenue_yoy" and re.search(r"forecast|anticipated|terminal|valuation|compound annual|gross profit margin",text): return "Excluded from analysis: growth refers to a forecast, valuation assumption, or another metric"
    if metric=="inventory_days":
        if re.fullmatch(r"\d+\)",raw.strip()) or "calculated based" in text: return "Excluded from analysis: extracted value is a footnote or formula reference"
        if "respectively" in text or len(re.findall(r"\b20\d{2}\b",text))>=2: return "Excluded from analysis: multi-year sentence could not be aligned safely to the current period"
    if metric=="average_selling_price" and (not re.search(r"rmb|hkd|cny|usd|us\$",raw_lower) or re.search(r"million|billion",raw_lower)): return "Excluded from analysis: candidate appears to be a volume or non-currency value"
    return ""

def main(stock_code:str|None=None, no_llm:bool=True):
    schema=yaml.safe_load((ROOT/"config/extraction_schema.yaml").read_text()); inventory=read_csv("data/processed/document_inventory.csv")
    evidence=[] if not stock_code else [x for x in read_csv("data/processed/metric_evidence.csv") if x["stock_code"]!=stock_code.zfill(5)]
    wide=[] if not stock_code else [x for x in read_csv("data/processed/company_year_metrics.csv") if x["stock_code"]!=stock_code.zfill(5)]
    for doc in inventory:
        if stock_code and doc["stock_code"]!=stock_code.zfill(5): continue
        md_rel=f"data/interim/markdown/{doc['stock_code']}/{doc['financial_year']}/annual_report.md"; path=ROOT/md_rel
        if not path.exists(): continue
        text=path.read_text(errors="replace"); pages=split_pages(text); page_index=[(n,p,p.lower()) for n,p in pages]; fm=frontmatter(text); row={"stock_code":doc["stock_code"],"company_name":doc["company_name"],"industry":doc["industry"],"financial_year":int(doc["financial_year"])}
        typer.echo(f"Extracting metrics {doc['stock_code']} FY{doc['financial_year']}")
        for metric,spec in schema["metrics"].items():
            found=None
            aliases=spec.get("aliases",[]); aliases_lower=[a.lower() for a in aliases]
            for page_no,page,page_lower in page_index:
                if not any(alias in page_lower for alias in aliases_lower): continue
                candidate=find_metric(page,aliases,spec.get("type","number"),spec.get("unit",""))
                if candidate: found=(page_no,page,candidate); break
            base={"stock_code":doc["stock_code"],"company_name":doc["company_name"],"industry":doc["industry"],"financial_year":int(doc["financial_year"]),"report_title":doc["document_title"],"metric":metric,"hkex_result_page_url":doc.get("hkex_url",""),"source_document_url":doc.get("pdf_url",""),"local_pdf_path":doc.get("local_pdf_path",""),"local_markdown_path":md_rel}
            if found:
                page_no,page,(value,raw,start,end,snippet)=found; unit="%" if spec.get("type")=="percentage" else spec.get("unit","")
                excluded=exclusion_reason(metric,raw,snippet)
                item={**base,"value":value,"unit":unit,"value_raw":raw,"pdf_page":page_no,"evidence_text":snippet,"evidence_text_start_char":start,"evidence_text_end_char":end,"extraction_method":"regex_page","confidence":.72 if not excluded else .2,"validation_status":"excluded" if excluded else "needs_review","missing_reason":excluded}; row[metric]=None if excluded else value
            else:
                item={**base,"value":None,"unit":"%" if spec.get("type")=="percentage" else spec.get("unit",""),"value_raw":"","pdf_page":None,"evidence_text":"","extraction_method":"not_found","confidence":0,"validation_status":"missing","missing_reason":"No matching label and value found in extracted annual-report text"}; row[metric]=None
            evidence.append(Evidence.model_validate(item).model_dump())
        hits,tone=narrative_signals(pages,schema["narrative_themes"]["negative"],schema["narrative_themes"]["positive"]); row["management_tone_negative"]=tone; row["management_tone_summary"]=(f"{sum(h['tone']=='negative' for h in hits)} negative and {sum(h['tone']=='positive' for h in hits)} positive grounded theme hits" if hits else "No configured narrative themes found")
        tone_base={"stock_code":doc["stock_code"],"company_name":doc["company_name"],"industry":doc["industry"],"financial_year":int(doc["financial_year"]),"report_title":doc["document_title"],"metric":"management_tone_negative","hkex_result_page_url":doc.get("hkex_url",""),"source_document_url":doc.get("pdf_url",""),"local_pdf_path":doc.get("local_pdf_path",""),"local_markdown_path":md_rel}
        if hits:
            snippets=" | ".join(f"[{h['tone']}: {h['term']}] {h['evidence_text']}" for h in hits[:3])
            tone_item={**tone_base,"value":tone,"unit":"ratio","value_raw":str(tone),"pdf_page":hits[0]["pdf_page"],"evidence_text":snippets,"extraction_method":"keyword_theme","confidence":.65,"validation_status":"needs_review","missing_reason":""}
        else:
            tone_item={**tone_base,"value":None,"unit":"ratio","value_raw":"","pdf_page":None,"evidence_text":"","extraction_method":"not_found","confidence":0,"validation_status":"missing","missing_reason":"No configured management-tone themes found"}
        evidence.append(Evidence.model_validate(tone_item).model_dump())
        wide.append(row)
    write_csv("data/processed/company_year_metrics.csv",wide); write_json("data/processed/company_year_metrics.json",wide)
    fields=list(Evidence.model_fields); write_csv("data/processed/metric_evidence.csv",evidence,fields)
    p=ROOT/"data/processed/metric_evidence.jsonl"; p.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in evidence))
    missing=[x for x in evidence if x["validation_status"] in ("missing","excluded")]; write_csv("data/processed/unsupported_or_missing_metrics.csv",missing,fields)
    metric_map={(x["stock_code"],str(x["financial_year"])):x for x in wide}; quality=read_csv("data/processed/extraction_quality_log.csv")
    for q in quality:
        reasons=[x for x in q.get("reason","").split("; ") if x]; row=metric_map.get((q["stock_code"],str(q["financial_year"])),{})
        if row.get("revenue_total") in (None,""): reasons.append("no revenue value found")
        md=ROOT/f"data/interim/markdown/{q['stock_code']}/{q['financial_year']}/annual_report.md"; md_lower=md.read_text(errors="replace").lower() if md.exists() else ""
        if "management discussion" not in md_lower: reasons.append("no management discussion section found")
        q["needs_manual_review"]=bool(reasons); q["reason"]="; ".join(dict.fromkeys(reasons))
    write_csv("data/processed/extraction_quality_log.csv",quality)
    typer.echo(f"Extracted {len(evidence)-len(missing)} values; recorded {len(missing)} explicit missing values")
if __name__=="__main__": typer.run(main)
