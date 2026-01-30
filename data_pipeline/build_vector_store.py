#Creating embeddings, vector index & implementing FAISS(manages vector indexes)

import json
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer

DATA_DIR = Path("data")
CHUNKS_DIR = DATA_DIR / "chunks"
VECTOR_DIR = DATA_DIR / "vector_store"
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_FILES=[
    CHUNKS_DIR/"core_docs_chunks.json",
    CHUNKS_DIR/"circulars_chunks.json",
    CHUNKS_DIR/"live_sources_chunks.json",
]
RULES_FAISS_INDEX_FILE = VECTOR_DIR / "rules_faiss.index"
RULES_METADATA_FILE = VECTOR_DIR / "rules_metadata.json"
LIVE_FAISS_INDEX_FILE = VECTOR_DIR / "live_faiss.index"
LIVE_METADATA_FILE = VECTOR_DIR / "live_metadata.json"

model=SentenceTransformer("all-MiniLM-L6-v2")
rules_texts=[]
rules_metadata=[]
live_texts=[]
live_metadata=[]
for file in CHUNK_FILES:
    if not file.exists():
        continue
    with open(file,"r",encoding="utf-8") as f:
        records=json.load(f)
    for rec in records:
        meta = {
            "chunk_id": rec["chunk_id"],
            "document_path": rec["document_path"],
            "doc_category": rec["doc_category"],
            "rule_type": rec["rule_type"],
            "priority": rec["priority"],
            "page_number": rec["page_number"],
            "section_index": rec["section_index"],
            "authority": rec.get("authority"),
            "is_static": rec.get("is_static"),
            "effective_year": rec.get("effective_year"),
            "text": rec.get("text")
        }
        if rec["doc_category"] == "live_source":
            live_texts.append(rec["text"])
            live_metadata.append(meta)
        else:
            rules_texts.append(rec["text"])
            rules_metadata.append(meta)

rules_embeddings = model.encode(
    rules_texts,
    batch_size=32,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)
rules_index = faiss.IndexFlatIP(rules_embeddings.shape[1])
rules_index.add(rules_embeddings)
faiss.write_index(rules_index,str(RULES_FAISS_INDEX_FILE))
with open(RULES_METADATA_FILE, "w", encoding="utf-8") as f:
    json.dump(rules_metadata, f, indent=2, ensure_ascii=False)

live_embeddings = model.encode(
    live_texts,
    batch_size=32,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)
live_index = faiss.IndexFlatIP(live_embeddings.shape[1])
live_index.add(live_embeddings)
faiss.write_index(live_index, str(LIVE_FAISS_INDEX_FILE))
with open(LIVE_METADATA_FILE,"w",encoding="utf-8") as f:
    json.dump(live_metadata, f, indent=2, ensure_ascii=False)

print(f"Rules chunks loaded     : {len(rules_texts)}")
print(f"Live source chunks loaded: {len(live_texts)}")
print(f"Rules FAISS index size  : {rules_index.ntotal}")
print(f"Live FAISS index size   : {live_index.ntotal}")
print("✅ Embeddings and FAISS index saved successfully.")