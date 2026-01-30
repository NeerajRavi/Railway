import json
import re
from pathlib import Path

data_dir = Path("data")
extract_dir = data_dir / "extracted_text"
chunks_dir = data_dir / "chunks"
chunks_dir.mkdir(parents=True, exist_ok=True)

input_files = {
    "core_docs": extract_dir / "core_docs.json",
    "circulars": extract_dir / "circulars.json",
    "live_sources": extract_dir / "live_sources.json",
}

CHUNK_WORDS = 600
OVERLAP_WORDS = 120
SECTION_PATTERN = re.compile(r"(?:^|\n)\s*(\d+\.\d+)\s+")

def split_into_sections(text):
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return [text]
    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if section_text:
            sections.append(section_text)
    return sections

def chunk_by_words(text, chunk_size, overlap):
    words = text.split()
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    step = chunk_size - overlap
    for start in range(0, len(words), step):
        end = start + chunk_size
        chunk_words = words[start:end]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
    return chunks

#Main splitting
for source_name, input_file in input_files.items():
    with open(input_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    chunked_records = []
    for rec in records:
        text = rec.get("text", "").strip()
        if not text:
            continue
        sections = split_into_sections(text)
        for sec_idx, section in enumerate(sections, start=1):
            section_chunks = chunk_by_words(
                section,
                CHUNK_WORDS,
                OVERLAP_WORDS
            )
            for chunk_idx, chunk in enumerate(section_chunks, start=1):
                chunk_record = {
                    "chunk_id": (
                        f"{rec['document_path'].replace('/', '_')}"
                        f"_p{rec.get('page_number')}"
                        f"_s{sec_idx}"
                        f"_c{chunk_idx}"
                    ),
                    "document_path": rec.get("document_path"),
                    "doc_category": rec.get("doc_category"),
                    "rule_type": rec.get("rule_type"),
                    "priority": rec.get("priority"),
                    "authority": rec.get("authority"),
                    "is_static": rec.get("is_static"),
                    "effective_year": rec.get("effective_year"),
                    "page_number": rec.get("page_number"),
                    "section_index": sec_idx,
                    "chunk_index": chunk_idx,
                    "text": chunk
                }
                chunked_records.append(chunk_record)
    output_file = chunks_dir / f"{source_name}_chunks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunked_records, f, indent=2, ensure_ascii=False)
    print(f"✅ {source_name}: {len(chunked_records)} chunks created")