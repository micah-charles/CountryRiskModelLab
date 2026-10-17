from __future__ import annotations
import re

def narrative_signals(pages, negative, positive):
    hits=[]
    for page_no,text in pages:
        lower=text.lower()
        for tone, terms in (("negative",negative),("positive",positive)):
            for term in terms:
                if term.lower() not in lower: continue
                m=re.search(rf"(?is).{{0,100}}\b{re.escape(term)}\b.{{0,180}}", text)
                if m: hits.append({"tone":tone,"term":term,"pdf_page":page_no,"evidence_text":" ".join(m.group().split())})
    neg=sum(h["tone"]=="negative" for h in hits); pos=sum(h["tone"]=="positive" for h in hits)
    return hits, (neg/(neg+pos) if neg+pos else None)
