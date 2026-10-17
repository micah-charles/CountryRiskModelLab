from __future__ import annotations
import re

TOKEN = re.compile(r"(?i)(?P<prefix>RMB|HKD|CNY|US\$|USD)?\s*(?P<value>[-+]?\(?\d[\d,]*(?:\.\d+)?\)?)(?P<suffix>\s*(?:%|million|billion|thousand|yuan|days|times)?)")

def parse_number(raw: str):
    clean=raw.lower().replace(",", "").strip(); negative=bool(re.match(r"^\s*\([^)]*\)", clean))
    clean=clean.strip("() "); m=re.search(r"[-+]?\d+(?:\.\d+)?", clean)
    if not m: return None
    value=float(m.group());
    if negative: value=-value
    if "billion" in clean: value*=1_000_000_000
    elif "million" in clean: value*=1_000_000
    elif "thousand" in clean: value*=1_000
    return value

def find_metric(page_text: str, aliases: list[str], metric_type: str, unit: str = ""):
    for alias in sorted(aliases, key=len, reverse=True):
        for line_match in re.finditer(rf"(?im)^.*\b{re.escape(alias)}\b.*$", page_text):
            line=line_match.group(0); alias_match=re.search(re.escape(alias),line,re.I)
            if not alias_match: continue
            tail=line[alias_match.end():]
            for token in TOKEN.finditer(tail):
                raw=token.group(0).strip(); suffix=token.group("suffix").lower(); prefix=token.group("prefix") or ""
                bare=token.group("value").replace(",","").strip("()")
                if token.group("value").startswith("(") and len(bare)<=2: continue  # footnote marker
                if metric_type=="percentage" and "%" not in suffix: continue
                if metric_type!="percentage" and "%" in suffix: continue
                if unit=="currency" and not (prefix or any(x in suffix for x in ("million","billion","thousand","yuan"))): continue
                if unit!="currency" and prefix: continue
                if metric_type=="number" and unit!="currency" and bare.isdigit() and 1990<=int(bare)<=2100: continue
                before=tail[max(0,token.start()-12):token.start()].lower(); after=tail[token.end():token.end()+12].lower()
                if metric_type=="percentage" and "by" in before and "point" in after: continue
                value=parse_number(raw)
                if value is not None:
                    start=line_match.start()+alias_match.end()+token.start(); end=line_match.start()+alias_match.end()+token.end()
                    return value, raw, start, end, line.strip()
    return None
