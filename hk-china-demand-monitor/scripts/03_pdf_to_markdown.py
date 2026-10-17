from __future__ import annotations
import typer, yaml
from _bootstrap import ROOT
from src.common import read_csv, write_csv, relative, now_iso
from src.pdf.extract_text import extract_pages
from src.pdf.ocr import ocr_pdf
from src.pdf.markdown_cleaner import to_markdown
from src.pdf.tables import extract_tables

def main(stock_code:str|None=None, force_ocr:bool=False, extract_tables_flag:bool=typer.Option(False,"--extract-tables")):
    inventory=read_csv("data/processed/document_inventory.csv")
    quality=[] if not stock_code else [x for x in read_csv("data/processed/extraction_quality_log.csv") if x["stock_code"]!=stock_code.zfill(5)]
    sources=[] if not stock_code else [x for x in read_csv("data/processed/source_documents.csv") if x["stock_code"]!=stock_code.zfill(5)]
    page_index=[] if not stock_code else [x for x in read_csv("data/processed/source_page_index.csv") if x["stock_code"]!=stock_code.zfill(5)]
    for row in inventory:
        if stock_code and row["stock_code"]!=stock_code.zfill(5): continue
        pdf=ROOT/row["local_pdf_path"]
        if not pdf.exists(): continue
        typer.echo(f"Extracting {row['stock_code']} FY{row['financial_year']} ({pdf.stat().st_size/1_000_000:.1f} MB)")
        pages,stats=extract_pages(pdf); method="embedded_text"; ocr_stats={"ocr_confidence":"","ocr_pages":0}
        raw=f"data/interim/pdf_text/{row['stock_code']}/{row['financial_year']}/raw_text.txt"; (ROOT/raw).parent.mkdir(parents=True,exist_ok=True); (ROOT/raw).write_text("\n\f\n".join(pages))
        if force_ocr or stats["quality_score"] < .65:
            try:
                ocr_pages,ocr_stats=ocr_pdf(pdf); ocr_path=ROOT/f"data/interim/ocr_text/{row['stock_code']}/{row['financial_year']}/ocr_text.txt"; ocr_path.parent.mkdir(parents=True,exist_ok=True); ocr_path.write_text("\n\f\n".join(ocr_pages))
                if force_ocr or sum(map(len,ocr_pages)) > sum(map(len,pages)): pages=ocr_pages; method="ocr"
                else: method="hybrid"
            except Exception as exc: stats["ocr_error"]=str(exc)
        md_rel=f"data/interim/markdown/{row['stock_code']}/{row['financial_year']}/annual_report.md"
        fm={"stock_code":row["stock_code"],"company_name":row["company_name"],"industry":row["industry"],"financial_year":int(row["financial_year"]),"report_title":row["document_title"],"source_pdf":row["local_pdf_path"],"hkex_url":row.get("hkex_url",""),"pdf_url":row.get("pdf_url",""),"extraction_method":method,"extraction_quality_score":stats["quality_score"]}
        (ROOT/md_rel).parent.mkdir(parents=True,exist_ok=True); (ROOT/md_rel).write_text(to_markdown(fm,pages))
        if extract_tables_flag:
            try: extract_tables(pdf,f"data/interim/tables/{row['stock_code']}/{row['financial_year']}")
            except Exception as exc: typer.echo(f"Table extraction warning: {exc}")
        for i,text in enumerate(pages,1): page_index.append({"stock_code":row["stock_code"],"financial_year":row["financial_year"],"pdf_page":i,"local_markdown_path":md_rel,"page_text_available":bool(text.strip()),"ocr_used":method in ("ocr","hybrid"),"ocr_confidence":ocr_stats.get("ocr_confidence",""),"page_text_preview":" ".join(text[:240].split())})
        reason=[]
        if stats["quality_score"]<.65: reason.append("quality_score below 0.65")
        if method=="ocr": reason.append("OCR required")
        quality.append({"stock_code":row["stock_code"],"financial_year":row["financial_year"],"total_pages":stats["total_pages"],"pages_with_text":stats["pages_with_text"],"extraction_method":method,"quality_score":stats["quality_score"],"needs_manual_review":bool(reason),"reason":"; ".join(reason)})
        sources.append({"stock_code":row["stock_code"],"company_name":row["company_name"],"financial_year":row["financial_year"],"report_title":row["document_title"],"hkex_result_page_url":row.get("hkex_url",""),"source_document_url":row.get("pdf_url",""),"local_pdf_path":row["local_pdf_path"],"download_method":row.get("source_method",""),"download_timestamp":row.get("crawl_timestamp",now_iso()),"sha256":row.get("sha256",""),"page_count":stats["total_pages"],"status":"processed"})
    write_csv("data/processed/extraction_quality_log.csv",quality); write_csv("data/processed/source_documents.csv",sources); write_csv("data/processed/source_page_index.csv",page_index)
    typer.echo(f"Processed {len(quality)} reports")
if __name__=="__main__": typer.run(main)
