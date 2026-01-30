# Railway Rules RAG Module
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from modules.railway_rag.retrieval_engine import retrieve_rules
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = "gpt-4.1-mini"
SYSTEM_PROMPT = (
    "You are a railway rules assistant.\n"
    "You must answer the user question ONLY if the provided railway rules, clearly and directly contain the answer.\n"
    "Do not use any information outside the given rules.\n"
    "Do not speculate or infer missing details.\n"
    "If the rules do not clearly answer the question, do not attempt to answer."
)
def build_context(chunks):                  #Make all chunks into one block(in dec order of similarity for chunks)
    blocks = []                             #Creates text out of all retrieved chunks, For llm to read it like a document
    for i, c in enumerate(chunks, start=1):
        blocks.append(
            f"[Source {i}]\n"
            f"Document: {c['document_path']}\n"
            f"Authority: {c.get('authority')}\n"
            f"Page: {c.get('page_number')}, "
            f"Section: {c.get('section_index')}\n"
            f"Text:\n{c['text']}\n"
        )
    return "\n\n".join(blocks)
def extract_citations(chunks):               #Citations
    return [
        {
            "document_path": c.get("document_path"),
            "authority": c.get("authority"),
            "rule_type": c.get("rule_type"),
            "page_number": c.get("page_number"),
            "section_index": c.get("section_index"),
            "effective_year":c.get("effective_year")
        }
        for c in chunks            #For each chunk
    ]

def estimate_confidence(chunks):    #Find Confidence
    if not chunks:
        return 0.0
    # Collect similarities (LLM used all of them)
    sims = [c.get("similarity", 0.0) for c in chunks]
    # Best supporting rule
    top_sim = max(sims)
    # No strong rule at all → low confidence
    if top_sim < 0.45:
        return round(top_sim * 0.8, 2)
    # Consider only chunks that genuinely support the answer
    # (close enough to the best one)
    support_sims = [
        s for s in sims
        if s >= top_sim - 0.10
    ]
    # Mean support from all relevant chunks
    support_mean = sum(support_sims) / len(support_sims)
    # Final confidence
    confidence = (
        0.75 * top_sim +
        0.25 * support_mean
    )
    return round(min(confidence, 0.9), 2)

def answer_with_rag(query: str):
    chunks = retrieve_rules(query)
    if not chunks:  # No chunks
        return {
            "answer": None,
            "has_answer": False,
            "meta": {"confidence": 0.0,}
        }
    context=build_context(chunks)
    user_prompt=(
        f"User question:\n{query}\n\n"
        f"Relevant railway rules:\n{context}\n\n"
        "Instructions:\n"
        "- Answer strictly using the rules above.\n"
        "- Do not add external knowledge.\n"
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    answer_text = response.choices[0].message.content.strip()
    confidence=estimate_confidence(chunks)
    if not answer_text:
        return {
            "answer": None,
            "has_answer": False,
            "meta": {
                "confidence": confidence
            }
        }
    return {
        "answer": answer_text,
        "has_answer": confidence>=0.45,
        "meta": {
            "confidence": confidence,
            "citations": extract_citations(chunks),
            "rule_types": list({c.get("rule_type") for c in chunks if c.get("rule_type")})
        }
    }
if __name__ == "__main__":
    print("✅ Railway base RAG module ready.")