import { chromium } from "playwright"; import fs from "node:fs"; import path from "node:path";
const root=new URL("..",import.meta.url).pathname; const browser=await chromium.launch({headless:true}); const page=await browser.newPage(); const failures:string[]=[]; const ids:Record<string,string>={"06862":"199151","02020":"16111","01211":"2696"};
for(const [code,stockId] of Object.entries(ids)){
  try{await page.goto(`https://www1.hkexnews.hk/search/titlesearch.xhtml?category=0&market=SEHK&stockId=${stockId}`,{waitUntil:"domcontentloaded",timeout:45000}); const rows=page.locator("#titleSearchResultPanel tbody tr"); await rows.first().waitFor({timeout:20000}); const annual=(await rows.allTextContents()).filter(x=>/annual report|年報|年度報告/i.test(x)&&!/environmental.*social.*governance/i.test(x));if(!annual.length)failures.push(`${code}: no annual report row`);await page.screenshot({path:`${root}/logs/screenshots/qa_hkex_${code}.png`,fullPage:true});}catch(e){failures.push(`${code}: ${e}`)}
}
function walk(dir:string):string[]{return fs.existsSync(dir)?fs.readdirSync(dir,{withFileTypes:true}).flatMap(x=>x.isDirectory()?walk(path.join(dir,x.name)):[path.join(dir,x.name)]):[]}
const pdfs=walk(`${root}/data/raw/annual_reports`).filter(x=>x.endsWith(".pdf"));if(!pdfs.some(x=>fs.statSync(x).size>1000&&fs.readFileSync(x).subarray(0,4).toString()==="%PDF"))failures.push("no readable cached PDF");
const markdown=walk(`${root}/data/interim/markdown`).filter(x=>x.endsWith(".md"));if(!markdown.some(x=>{const t=fs.readFileSync(x,"utf8");return t.startsWith("---")&&t.includes("<!-- page:")}))failures.push("no page-marked Markdown");
const report=`${root}/data/reports/china_domestic_demand_summary.html`; if(fs.existsSync(report)){await page.goto(`file://${report}`); if(!(await page.title())) failures.push("HTML report has no title");}
await browser.close(); if(failures.length){console.error(failures.join("\n"));process.exitCode=1}else console.log("Browser QA passed");
