from __future__ import annotations
from pathlib import Path
from src.common import resolve

def available_languages():
    try:
        import pytesseract; return set(pytesseract.get_languages(config=""))
    except Exception: return set()

def ocr_pdf(path: str | Path, dpi: int = 220) -> tuple[list[str], dict]:
    import fitz, pytesseract
    from PIL import Image
    langs = available_languages(); selected = "+".join(x for x in ("eng","chi_sim","chi_tra") if x in langs) or "eng"
    doc = fitz.open(resolve(path)); output=[]; confidences=[]
    scale=dpi/72
    for page in doc:
        pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale), alpha=False)
        image=Image.frombytes("RGB", [pix.width,pix.height], pix.samples)
        data=pytesseract.image_to_data(image, lang=selected, output_type=pytesseract.Output.DICT)
        output.append(" ".join(x for x in data["text"] if x.strip()))
        vals=[float(x) for x in data["conf"] if str(x) not in ("-1", "")]
        confidences.extend(vals)
    confidence=(sum(confidences)/max(1,len(confidences)))/100
    return output, {"languages":selected,"ocr_confidence":round(confidence,4),"ocr_pages":len(output)}

