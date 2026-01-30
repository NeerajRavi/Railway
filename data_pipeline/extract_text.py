import json
import re
from pathlib import Path
from pypdf import PdfReader
import pytesseract
pytesseract.pytesseract.tesseract_cmd=r"D:\OCR\tesseract.exe"  # Give correct path
import fitz
from PIL import Image
import io

base_dir=Path(__file__).parent.parent
# print(base_dir)
data=base_dir/"data"
raw_docs=data/"raw_docs"
circulars=raw_docs/"circulars"
core_docs=raw_docs/"core_docs"
live_sources_file=raw_docs/"live_sources"/"live_sources.json"
metadata_file=raw_docs/"meta_data.json"

output_dir=data/"extracted_text"
output_dir.mkdir(parents=True,exist_ok=True)

with open(metadata_file,"r",encoding="utf-8") as f:            # Reads core and circular folders metadata(custom made not program generated)
    file_metadata=json.load(f)
# print(file_metadata["core_docs/Railways_Act_1989.pdf"])

def clean_text(text):    #Converts to cleaned str
    text = re.sub(r"\n{3,}","\n\n",text)
    text=re.sub(r"[ ]{2,} | \t+"," ",text)
    return text.strip()

def ocr_pdf(pdf_path):   #Reads images in pdfs
    doc = fitz.open(pdf_path)
    pages_text = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=300)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="eng")
        if text.strip():
            pages_text.append((i, text))
    return pages_text

def extract_pdf(pdf_path, relative_key):
    records = []
    meta = file_metadata.get(relative_key)
    if not meta:
        print(f"[WARNING] Metadata missing for {relative_key}")
        return records
    reader = PdfReader(str(pdf_path))
    has_text = False
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            has_text = True
            break
    if has_text:
        for page_no, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if not text:
                continue
            records.append({
                "document_id": relative_key.replace("/", "__"),
                "document_name": pdf_path.name,
                "document_path": relative_key,
                "doc_category": meta.get("doc_category"),
                "rule_type": meta.get("rule_type"),
                "priority": meta.get("priority"),
                "authority": meta.get("authority"),
                "description": meta.get("description"),
                "is_static": meta.get("is_static"),
                "effective_year": meta.get("effective_year"),
                "page_number": page_no,
                "text": clean_text(text),
                "extraction_method": "text"
            })
    else:
        ocr_pages = ocr_pdf(pdf_path)
        if not ocr_pages:
            print(f"[OCR FAILED] {relative_key}")
        for page_no, ocr_text in ocr_pages:
            records.append({
                "document_id": relative_key.replace("/", "__"),
                "document_name": pdf_path.name,
                "document_path": relative_key,
                "doc_category": meta.get("doc_category"),
                "rule_type": meta.get("rule_type"),
                "priority": meta.get("priority"),
                "authority": meta.get("authority"),
                "description": meta.get("description"),
                "is_static": meta.get("is_static"),
                "effective_year": meta.get("effective_year"),
                "page_number": page_no,
                "text": clean_text(ocr_text),
                "extraction_method": "ocr"
            })
    return records


def process_folder(base_folder,category_name):
    all_records=[]
    for pdf_file in base_folder.rglob("*.pdf"):
        relative_path=pdf_file.relative_to(base_folder).as_posix()
        relative_key=f"{category_name}/{relative_path}"
        print(f"Processing: {relative_key}")
        records=extract_pdf(pdf_file, relative_key)    #Calls extract function
        if not records:
            print(f"[SKIPPED] No extractable text: {relative_key}")
        all_records.extend(records)
    return all_records

def process_live_sources():
    with open(live_sources_file,"r",encoding="utf-8") as f:
        live_sources=json.load(f)
    records=[]
    for item in live_sources:
        record={
            "document_name": item.get("name"),
            "document_path": item.get("url"),
            "doc_category": "live_source",
            "rule_type": item.get("rule_type"),
            "priority": item.get("priority"),
            "authority": item.get("authority"),
            "description": item.get("description"),
            "is_static": False,
            "effective_year": None,
            "page_number": None,
            "text":clean_text(item.get("description",""))
        }
        records.append(record)
    return records

if __name__=="__main__":
    core_records=process_folder(core_docs,"core_docs")
    circular_records=process_folder(circulars,"circulars")
    live_records=process_live_sources()
    with open(output_dir/"core_docs.json","w",encoding="utf-8") as f:
        json.dump(core_records,f,indent=2,ensure_ascii=False)
    with open(output_dir/"circulars.json","w",encoding="utf-8") as f:
        json.dump(circular_records,f,indent=2,ensure_ascii=False)
    with open(output_dir/"live_sources.json","w",encoding="utf-8") as f:
        json.dump(live_records,f,indent=2,ensure_ascii=False)
    print("\n✅ Document ingestion completed successfully.")