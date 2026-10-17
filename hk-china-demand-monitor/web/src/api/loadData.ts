export type Row=Record<string,string|number|boolean|null>;
const names=["company_universe","document_inventory","company_year_metrics","demand_pressure_scores","industry_summary","metric_evidence","source_documents","source_page_index","quality_warnings"] as const;
export type Data=Record<(typeof names)[number],Row[]>;
export async function loadData():Promise<Data>{const entries=await Promise.all(names.map(async n=>[n,await fetch(`/data/${n}.json`).then(r=>r.ok?r.json():[])]));return Object.fromEntries(entries) as Data}
