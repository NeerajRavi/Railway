# Retrieves links for all modules
import json
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer
DATA_DIR = Path("data")
VECTOR_DIR = DATA_DIR / "vector_store"
LIVE_FAISS_INDEX_PATH = VECTOR_DIR / "live_faiss.index"
LIVE_METADATA_PATH = VECTOR_DIR / "live_metadata.json"
index = faiss.read_index(str(LIVE_FAISS_INDEX_PATH))
with open(LIVE_METADATA_PATH, "r", encoding="utf-8") as f:
    METADATA = json.load(f)
model = SentenceTransformer("all-MiniLM-L6-v2")
def retrieve_live_sources(
    query: str,
    *,
    top_k: int = 2,
    search_k: int = 2000
):
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    scores, indices = index.search(query_embedding, search_k)
    results = []
    seen_urls = set()
    for score, idx in zip(scores[0], indices[0]):
        meta = METADATA[idx]
        url = meta.get("document_path")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        results.append({
            "url": url,
            "authority": meta.get("authority"),
            "description": meta.get("text"),
            "similarity": float(score)
        })
        if len(results) >= top_k:
            break
    return results