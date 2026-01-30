import os
import json
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL_NAME = "gpt-4.1-mini"

ROUTER_SYSTEM_PROMPT = (
    "You are a routing system for a multi-module assistant.\n"
    "Your task is to rank ALL available modules by how suitable they are\n"
    "for handling the user's input.\n\n"

    "Available modules:\n"
    "- railway_rag : authoritative, static, rule-based railway information such as\n"
    "               laws, regulations, penalties, permissions, procedures, and\n"
    "               official policies derived from documents.\n\n"

    "- live_data_apis : dynamic or time-sensitive railway information such as\n"
    "                   live train status, current location, delays, fares,\n"
    "                   seat availability, PNR status, or other real-time data.\n\n"

    "- general : conversational, explanatory, or contextual input such as\n"
    "            greetings, clarifications, follow-up questions, or general\n"
    "            explanations that do not require authoritative rules or live data.\n\n"

    "- link_answer : providing official railway website links ONLY when the user explicitly asks for links, sources, websites, or external references, or when they request where to check information.\n\n"

    "Rules:\n"
    "- Rank ALL modules\n"
    "- Relevance must be between 0.0 and 1.0\n"
    "- Higher relevance means the module should be tried earlier\n"
    "- Do NOT explain your reasoning\n"
    "- Do NOT generate answers\n"
    "- Respond ONLY in valid JSON\n\n"

    "JSON format:\n"
    "{\n"
    '  "module_preferences": [\n'
    '    {"module": "railway_rag", "relevance": 0.0},\n'
    '    {"module": "live_data_apis", "relevance": 0.0},\n'
    '    {"module": "general", "relevance": 0.0},\n'
    '    {"module": "link_answer", "relevance": 0.0}\n'
    "  ]\n"
    "}"
)

VALID_MODULES = {"railway_rag", "live_data_apis", "general", "link_answer"}

def route_query(query):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ],
        temperature=0
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        prefs = parsed["module_preferences"]
    except Exception:
        # Explicit router failure (no guessing)
        return {
            "router_failed": True,
            "module_preferences": []
        }
    cleaned = []
    seen = set()
    for item in prefs:
        module = item.get("module")
        relevance = item.get("relevance")
        if module not in VALID_MODULES:
            continue
        try:
            relevance = float(relevance)
        except Exception:
            continue
        relevance=max(0.0,min(relevance,1.0))
        cleaned.append({"module": module, "relevance": relevance})   #Gives module name and relevance score in decreasing order
        seen.add(module)
    for m in VALID_MODULES:
        if m not in seen:
            cleaned.append({"module": m, "relevance": 0.0})
    cleaned.sort(key=lambda x: x["relevance"], reverse=True)
    print(cleaned)
    return {
        "router_failed": False,
        "module_preferences": cleaned,
    }