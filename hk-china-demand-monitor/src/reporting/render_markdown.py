from __future__ import annotations
from collections import Counter
from html import escape

def render(universe,documents,quality,metrics,scores,industries,evidence,run_meta=None):
    valid=[s for s in scores if s.get("demand_pressure_score") not in (None,"")]; avg=sum(float(s["demand_pressure_score"]) for s in valid)/len(valid) if valid else None
    avg_conf=sum(float(s.get("confidence") or 0) for s in valid)/len(valid) if valid else 0
    if avg is None or len(valid)<2 or avg_conf<.4: conclusion="there is currently insufficient supported coverage to classify the direction of domestic demand."
    elif avg>=3.5: conclusion="the available evidence suggests broad and material domestic-demand pressure, with important differences by industry."
    elif avg>=2: conclusion="the available evidence suggests mixed domestic-demand pressure rather than a broad collapse."
    else: conclusion="the available evidence is more consistent with stable or resilient demand, while some pockets may remain weak."
    lines=["# China Domestic Demand Monitor","","> Evidence-first output. Missing values are never estimated.","","## Executive summary","",f"Based on the annual-report evidence available, {conclusion}","",f"Coverage: {len(universe)} companies; {len(documents)} annual reports; {len(valid)} scored company-years.","","## Methodology","","Annual reports are preserved, converted page-by-page, and parsed with deterministic label patterns. Every candidate metric carries its source document, page, exact snippet, method, confidence, and validation status. Scores reweight across supported inputs only; low coverage reduces score confidence.","","## Universe coverage","","| Stock code | Company | Industry |","|---|---|---|"]
    lines += [f"| {x['stock_code']} | {x.get('name_en','')} | {x.get('industry','')} |" for x in universe]
    lines += ["","## Extraction quality","","| Stock | FY | Method | Quality | Review |","|---|---:|---|---:|---|"]
    lines += [f"| {x['stock_code']} | {x['financial_year']} | {x['extraction_method']} | {x['quality_score']} | {x['needs_manual_review']} |" for x in quality]
    lines += ["","## Industry findings","","| Industry | FY | Pressure score | Companies |","|---|---:|---:|---:|"]
    lines += [f"| {x['industry']} | {x['financial_year']} | {x['demand_pressure_score']} | {x['company_count']} |" for x in industries]
    smap={(x['stock_code'],str(x['financial_year'])):x for x in scores}
    lines += ["","## Company-by-company evidence summary","","| Stock | Company | Industry | FY | Revenue YoY | SSSG | Gross margin | Inventory days | Management tone | Score | Confidence |","|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|"]
    for x in metrics:
        s=smap.get((x['stock_code'],str(x['financial_year'])),{}); lines.append(f"| {x['stock_code']} | {x['company_name']} | {x['industry']} | {x['financial_year']} | {x.get('revenue_yoy','')} | {x.get('same_store_sales_growth','')} | {x.get('gross_margin','')} | {x.get('inventory_days','')} | {x.get('management_tone_summary','')} | {s.get('demand_pressure_score','')} | {s.get('confidence','')} |")
    verified=[x for x in evidence if x.get("validation_status") in ("verified","needs_review") and x.get("evidence_text")][:20]
    lines += ["","## Key evidence quotes"]
    for x in verified: lines += ["",f"- **{x['stock_code']} FY{x['financial_year']} · {x['metric']} = {x['value_raw']}** ({x['validation_status']}) — p.{x['pdf_page']}: “{x['evidence_text']}”"]
    statuses=Counter(x.get("validation_status") for x in evidence)
    lines += ["","## Data gaps and limitations","",f"Evidence statuses: {dict(statuses)}. Deterministic parsing may miss complex tables and ambiguous multi-column layouts. `needs_review` candidates should be checked against the cited page. Scores with low confidence are directional only.","","## Final conclusion","",f"Based on the annual-report evidence available, {conclusion}","","## Update Log","",f"```json\n{run_meta or {}}\n```",""]
    return "\n".join(lines)

def html_from_markdown(md):
    # Dependency-free readable HTML; dashboard is the interactive view.
    body="\n".join(f"<p>{escape(line)}</p>" for line in md.splitlines())
    return f"<!doctype html><html><meta charset='utf-8'><title>China Domestic Demand Monitor</title><style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.5}}p{{white-space:pre-wrap;margin:.25rem 0}}</style><body>{body}</body></html>"
