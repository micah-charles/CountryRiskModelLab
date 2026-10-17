import fitz
from PIL import Image,ImageDraw
from src.pdf.extract_text import extract_pages
from src.pdf.ocr import ocr_pdf
from src.pdf.markdown_cleaner import to_markdown,split_pages

def test_text_pdf_to_page_marked_markdown(tmp_path):
    p=tmp_path/"text.pdf"; d=fitz.open(); page=d.new_page(); page.insert_text((72,72),"Revenue RMB 12,345 million\nGross margin 62.5%\n"*20); d.save(p)
    pages,q=extract_pages(p); md=to_markdown({"stock_code":"02020"},pages)
    assert q["quality_score"]>.5 and "Revenue" in pages[0] and split_pages(md)[0][0]==1

def test_scanned_pdf_ocr(tmp_path):
    image=Image.new("RGB",(1600,1000),"white"); draw=ImageDraw.Draw(image); draw.text((100,300),"Annual Report 2024 Revenue 12345 Gross margin 62.5 percent",fill="black",font_size=42); png=tmp_path/"scan.png"; image.save(png)
    d=fitz.open(); page=d.new_page(width=800,height=500); page.insert_image(page.rect,filename=str(png)); p=tmp_path/"scan.pdf"; d.save(p)
    pages,meta=ocr_pdf(p,dpi=200); assert "Annual" in pages[0] and meta["ocr_pages"]==1

