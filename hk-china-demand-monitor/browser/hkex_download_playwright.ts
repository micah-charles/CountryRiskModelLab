import { chromium } from "playwright";
import fs from "node:fs"; import path from "node:path";

const arg=(name:string, fallback="")=>{const i=process.argv.indexOf(name); return i>=0?process.argv[i+1]:fallback};
const codes=arg("--codes").split(",").filter(Boolean); const years=Number(arg("--years","3")); const output=arg("--output","data/interim/hkex_discovered.json"); const headed=process.argv.includes("--headed");
const knownStockIds:Record<string,string>={"06862":"199151","02020":"16111","01211":"2696"};
const browser=await chromium.launch({headless:!headed}); const context=await browser.newContext({acceptDownloads:true}); const page=await context.newPage(); const found:any[]=[];
for(const stockCode of codes){
  try{
    const stockId=knownStockIds[stockCode]; const target=stockId?`https://www1.hkexnews.hk/search/titlesearch.xhtml?category=0&market=SEHK&stockId=${stockId}`:"https://www1.hkexnews.hk/search/titlesearch.xhtml";
    await page.goto(target,{waitUntil:"domcontentloaded",timeout:45000}); await page.waitForSelector("#searchStockCode",{timeout:20000});
    if(!stockId){
      const from=new Date(); from.setFullYear(from.getFullYear()-Math.max(4,years+1)); const fmt=(d:Date)=>`${d.getFullYear()}/${String(d.getMonth()+1).padStart(2,"0")}/${String(d.getDate()).padStart(2,"0")}`;
      await page.fill("#searchStockCode",stockCode); await page.waitForTimeout(1000); await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter");
      await page.evaluate(({fromValue,toValue})=>{for(const [selector,value] of [["#searchDate-From",fromValue],["#searchDate-To",toValue]] as const){const input=document.querySelector(selector) as HTMLInputElement|null;if(input){input.removeAttribute("readonly");input.value=value;input.dispatchEvent(new Event("change",{bubbles:true}));}}},{fromValue:fmt(from),toValue:fmt(new Date())}); await page.fill("#searchTitle","Annual Report"); await page.click(".filter__btn-applyFilters-js"); await page.waitForTimeout(3500);
    }
    await page.screenshot({path:`logs/screenshots/hkex_search_${stockCode}.png`,fullPage:true});
    const rows=page.locator("#titleSearchResultPanel tbody tr"); const count=await rows.count();
    for(let i=0;i<count;i++){
      const row=rows.nth(i); const text=(await row.innerText()).replace(/\s+/g," ").trim(); if(!/annual report|年報|年度報告/i.test(text)||/environmental.*social.*governance|esg report/i.test(text)) continue;
      const link=row.locator("a[href$='.pdf'], a[href*='.pdf?']").first(); if(!await link.count()) continue; const href=await link.getAttribute("href"); if(!href) continue;
      const pdfUrl=new URL(href,page.url()).href; const yearMatch=text.match(/(?:annual report\s*|年度報告\s*|年報\s*)(20\d{2})/i)||text.match(/(20\d{2})\s*(?:annual report|年度報告|年報)/i); const dateMatch=text.match(/(20\d{2})[\/\-]\d{1,2}[\/\-]\d{1,2}/); const dayFirst=text.match(/\d{1,2}[\/\-]\d{1,2}[\/\-](20\d{2})/); const financialYear=Number(yearMatch?.[1] || (dateMatch?Number(dateMatch[1])-1:dayFirst?Number(dayFirst[1])-1:0));
      found.push({stock_code:stockCode,financial_year:financialYear,document_title:text,pdf_url:pdfUrl,hkex_url:page.url(),source_method:"hkex_playwright",source_page_url:page.url(),discovered_pdf_url:pdfUrl,crawl_timestamp:new Date().toISOString(),confidence_score:yearMatch?0.95:0.75,reason_for_match:"HKEX row title matched annual-report pattern"});
      if(financialYear) await page.screenshot({path:`logs/screenshots/hkex_result_${stockCode}_${financialYear}.png`,fullPage:true});
    }
  }catch(error){fs.mkdirSync("logs",{recursive:true}); fs.writeFileSync(`logs/hkex_failure_${stockCode}.html`,await page.content()); await page.screenshot({path:`logs/screenshots/hkex_failure_${stockCode}.png`,fullPage:true}); console.error(stockCode,String(error));}
  await page.waitForTimeout(2000);
}
fs.mkdirSync(path.dirname(output),{recursive:true}); fs.writeFileSync(output,JSON.stringify(found,null,2)); await browser.close(); console.log(`Discovered ${found.length} candidate reports`);
