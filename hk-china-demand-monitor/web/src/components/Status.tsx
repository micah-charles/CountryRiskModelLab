export function Status({value}:{value:unknown}){const v=String(value||"missing");return <span className={`status ${v}`}>{v.replace("_"," ")}</span>}
