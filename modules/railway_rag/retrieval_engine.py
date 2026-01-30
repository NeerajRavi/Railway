#Helps railwaay_base_rag 
import json
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer

TOP_K_RETRIEVE = 50
TOP_K_FINAL = 10
SIMILARITY_THRESHOLD = 0.30
PRIORITY_WEIGHT = 0.15
RULE_MATCH_WEIGHT = 0.10
RECENCY_WEIGHT = 0.05
QUESTION_TYPE_WEIGHT = 0.10   
DATA_DIR = Path("data")
VECTOR_DIR = DATA_DIR / "vector_store"
RULES_FAISS_INDEX_PATH = VECTOR_DIR / "rules_faiss.index"
RULES_METADATA_PATH = VECTOR_DIR / "rules_metadata.json"
index = faiss.read_index(str(RULES_FAISS_INDEX_PATH))
with open(RULES_METADATA_PATH, "r", encoding="utf-8") as f:
    METADATA = json.load(f)
model = SentenceTransformer("all-MiniLM-L6-v2")
assert index.ntotal == len(METADATA), "Index and metadata size mismatch"

#Scoring helpers
def rule_match_score(query: str, rule_type: str) -> float:
    if not rule_type:
        return 0.0
    return 1.0 if rule_type.lower() in query.lower() else 0.0
def recency_score(year):
    if year is None:
        return 0.0
    return min((year - 2000) / 25, 1.0)
def detect_question_type(query: str) -> str:
    q = query.lower()
    if any(x in q for x in ["what is", "define", "meaning of"]):
        return "definition"
    if any(x in q for x in ["can i", "allowed", "permitted"]):
        return "permission"
    if any(x in q for x in ["not allowed", "prohibited", "shall not"]):
        return "prohibition"
    if any(x in q for x in ["how to", "procedure", "process"]):
        return "procedure"
    if any(x in q for x in ["penalty", "fine", "punishment", "liable"]):
        return "penalty"
    return "general"
def question_type_bonus(qtype: str, text: str) -> float:
    t = text.lower()
    if qtype == "definition" and any(x in t for x in ["means", "defined as"]):
        return QUESTION_TYPE_WEIGHT
    if qtype == "permission" and any(x in t for x in ["may", "permitted", "allowed"]):
        return QUESTION_TYPE_WEIGHT
    if qtype == "prohibition" and any(x in t for x in ["shall not", "prohibited"]):
        return QUESTION_TYPE_WEIGHT
    if qtype == "procedure" and any(x in t for x in ["procedure", "steps", "shall be"]):
        return QUESTION_TYPE_WEIGHT
    if qtype == "penalty" and any(x in t for x in ["penalty", "fine", "liable"]):
        return QUESTION_TYPE_WEIGHT
    return 0.0


def retrieve_rules(query: str):
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True
    )
    scores, indices = index.search(query_embedding, TOP_K_RETRIEVE)
    qtype = detect_question_type(query)
    candidates = []
    for i, idx in enumerate(indices[0]):
        similarity = float(scores[0][i])
        if similarity < SIMILARITY_THRESHOLD:
            continue
        meta = METADATA[idx]
        priority_bonus = (1 / meta["priority"]) * PRIORITY_WEIGHT
        rule_bonus = rule_match_score(query, meta["rule_type"]) * RULE_MATCH_WEIGHT
        recency_bonus = recency_score(meta.get("effective_year")) * RECENCY_WEIGHT
        qtype_bonus = question_type_bonus(qtype, meta["text"])
        final_score = (
            similarity
            + priority_bonus
            + rule_bonus
            + recency_bonus
            + qtype_bonus
        )
        candidates.append({
            "final_score": round(final_score, 4),
            "similarity": round(similarity, 4),
            "chunk_id": meta["chunk_id"],
            "document_path": meta["document_path"],
            "rule_type": meta["rule_type"],
            "priority": meta["priority"],
            "authority": meta["authority"],
            "page_number": meta["page_number"],
            "section_index": meta.get("section_index"),
            "text": meta["text"]
        })
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return candidates[:TOP_K_FINAL]