from __future__ import annotations

def pressure(value, thresholds=(-10, 0, 5)):
    if value is None: return None
    if value < thresholds[0]: return 5.0
    if value < thresholds[1]: return 4.0
    if value < thresholds[2]: return 2.0
    return 0.5

def score_row(row, previous, weights):
    components={}
    def get(name):
        try: return float(row[name]) if row.get(name) not in (None,"") else None
        except (ValueError,TypeError): return None
    components["revenue_china_yoy"] = pressure(get("revenue_yoy"))
    components["same_store_sales_growth"] = pressure(get("same_store_sales_growth"))
    components["customer_traffic_or_volume"] = pressure(get("customer_traffic_growth"))
    asp=get("average_selling_price"); pasp=float(previous.get("average_selling_price")) if previous and previous.get("average_selling_price") not in (None,"") else None
    ticket=get("average_spending_per_customer"); pticket=float(previous.get("average_spending_per_customer")) if previous and previous.get("average_spending_per_customer") not in (None,"") else None
    price_change=(100*(asp/pasp-1) if asp is not None and pasp not in (None,0) else (100*(ticket/pticket-1) if ticket is not None and pticket not in (None,0) else None))
    components["asp_or_average_ticket"] = pressure(price_change)
    gm=get("gross_margin"); pgm=float(previous.get("gross_margin")) if previous and previous.get("gross_margin") not in (None,"") else None
    components["gross_margin_change"] = pressure(gm-pgm if gm is not None and pgm is not None else None, (-3,0,1))
    inv=get("inventory_days"); pinv=float(previous.get("inventory_days")) if previous and previous.get("inventory_days") not in (None,"") else None
    components["inventory_days_change"] = pressure(-(inv-pinv) if inv is not None and pinv is not None else None, (-20,0,5))
    rec=get("receivable_days"); prec=float(previous.get("receivable_days")) if previous and previous.get("receivable_days") not in (None,"") else None
    components["receivable_days_change"] = pressure(-(rec-prec) if rec is not None and prec is not None else None, (-20,0,5))
    components["store_opening_momentum"] = pressure(get("net_store_openings"))
    tone=get("management_tone_negative"); components["management_tone_negative"] = 5*tone if tone is not None else None
    usable={k:v for k,v in components.items() if v is not None and weights.get(k,0)>0}
    denom=sum(weights[k] for k in usable)
    score=sum(v*weights[k] for k,v in usable.items())/denom if denom>=.18 and len(usable)>=2 else None
    confidence=min(1.0, denom/sum(weights.values())) if weights else 0
    return (round(max(0,min(5,score)),2) if score is not None else None), round(confidence,2), components
