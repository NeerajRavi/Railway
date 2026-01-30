# General module
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = "gpt-4.1-mini"
GENERAL_SYSTEM_PROMPT = (
    "You are a knowledgeable, helpful AI assistant.\n"
    "You can answer general questions, explain concepts clearly, "
    "and respond politely in a conversational manner.\n"
    "If a question is ambiguous, ask for clarification.\n"
    "Do not claim access to private, real-time, or restricted systems."
)
def get_relevance(route, module_name):
    for m in route.get("module_preferences", []):
        if m["module"] == module_name:
            return m["relevance"]
    return 0.0
def answer_general_query(query,route,mode="module"):
    if mode == "failsafe":
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
                {"role": "user", "content": query}],temperature=0.6)
        return {
            "answer": response.choices[0].message.content.strip(),
            "has_answer": True,
            "meta": {"mode": "failsafe"}}
    gen_rel = get_relevance(route, "general")
    rag_rel = get_relevance(route, "railway_rag")
    api_rel = get_relevance(route, "live_data_apis")
    MIN_GENERAL_RELEVANCE = 0.30
    DOMINANCE_MARGIN = 0.10
    if gen_rel < MIN_GENERAL_RELEVANCE:                        #Check 1
        return {
            "answer": None,
            "has_answer": False,
            "meta": {}
        }
    if gen_rel < max(rag_rel, api_rel) + DOMINANCE_MARGIN:      #Check 2
        return {
            "answer": None,
            "has_answer": False,
            "meta": {}
        }
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": GENERAL_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        temperature=0.6
    )
    answer_text = response.choices[0].message.content.strip()
    return {
        "answer": answer_text,
        "has_answer": True,
        "meta": {}
    }