# Main program...Combines all modules

import re
from Chatbot.router import route_query
from helpers.live_sources import retrieve_live_sources
from dotenv import load_dotenv
load_dotenv()
HIGH_CONF = 0.75
LOW_CONF = 0.45
LINK_RELEVANCE_MIN = 0.01
RELEVANCE_CLOSE_DELTA = 0.10

# Calling different modules
def call_railway_rag(query):
    from modules.railway_rag.railway_base_rag import answer_with_rag
    return answer_with_rag(query)
def call_live_data(query):
    from modules.live_data_apis import answer_with_live_data
    return answer_with_live_data(query)
def call_general(query,route,mode="module"):
    from modules.general_chat import answer_general_query
    return answer_general_query(query,route,mode)
def call_link_answer(query, num_of_links):
    from modules.link_answer import run
    src=run(query,num_of_links)
    if not src:
        return {"answer": None, "has_answer": False, "meta": {}}
    return {
        "answer": [s["url"] for s in src],
        "has_answer": True,
        "meta": {
            "status": "ok",
            "type": "links_only",
            "requested": num_of_links,
            "returned": len(src)
        }
    }

# Preliminary query check
def analyze_input_structure(query: str):
    q = query.strip()
    if not q:
        return "empty"
    if re.fullmatch(r"[^\w\s]+", q):
        return "noise"
    return "normal"
#Gets num of links
def extract_num_links(query, default=2, max_links=10):
    match = re.search(r"\b(\d+)\b", query)
    if match:
        return min(int(match.group(1)), max_links)
    return default
# Link adding reasons
def link_reason(reason_key: str):
    return {
        "rag_moderate": ("This answer is based on available railway rules. For official confirmation or additional details, please refer to:"),
        "api_stale": ("The available data may be outdated. For the latest official information, please refer to:"),
        "api_unknown": ("For authoritative and up-to-date information, please refer to:"),
        "general_info": ("For more detailed or official information, you may also refer to:"),
        "API_not_working":("The API is currently not working. For more information, please refer to:")
    }.get(reason_key, "For more information, please refer to:")

# Clean links
def format_live_sources(sources, reason):
    text = "\n\n" + reason + "\n"
    for s in sources:
        text += s["url"] + "\n"
    return text

#Main
def answer_query(query):
    structure = analyze_input_structure(query)
    if structure == "empty":
        return "Please enter a query so I can help you."
    if structure == "noise":
        return "I couldn’t understand the input. Please enter a clear question."
    # Calls router
    route = route_query(query)
    if route.get("router_failed"):
        return call_general(query,route,mode="failsafe")["answer"]
    preferences = route["module_preferences"]
    relevance_map = {m["module"]: m["relevance"] for m in preferences}
    tried = set()
    for pref in preferences:
        module = pref["module"]
        if module in tried:
            continue
        tried.add(module)
        # Link answer(links only)
        if module == "link_answer":
            num_links = extract_num_links(query)
            result = call_link_answer(query, num_links)
            if result.get("has_answer"):
                return "\n".join(result["answer"])
            continue
        # RAG
        if module == "railway_rag":
            result=call_railway_rag(query)
            if result.get("has_answer")==False:
                continue
            conf=result.get("meta",{}).get("confidence",0.0)
            if conf >= HIGH_CONF:
                return result["answer"]
            if LOW_CONF <= conf < HIGH_CONF:
                if relevance_map.get("link_answer",0) > LINK_RELEVANCE_MIN:
                    links = retrieve_live_sources(query)
                    if links:
                        return (
                            result["answer"]
                            + format_live_sources(
                                links,
                                reason=link_reason("rag_moderate")
                            )
                        )
                return result["answer"]
            continue  
        # Live data(APIs)
        if module == "live_data_apis":
            result=call_live_data(query)
            if result.get("has_answer")==False and result.get("meta",{}).get("status")=="nothing":
                continue
            if result.get("has_answer")==False and result.get("meta",{}).get("status")=="api_failed":
                links=retrieve_live_sources(query)
                reason="API_not_working"
                if links:
                    return (format_live_sources(links,reason=link_reason(reason)))
            if result.get("has_answer")==False and result.get("meta",{}).get("status")=="need_input":
                FIELD_LABELS = {
                "train_number": "Train number",
                "from_station": "Source station",
                "to_station": "Destination station",
                "date": "Journey date",
                "class_type": "Class (e.g., SL, 3A, 2A)",
                "quota": "Quota (GN / Tatkal)",
                "station_code": "Station name",
                "pnr": "PNR number",
                "hours": "Time window (in hours)"}
                missing=result.get("meta",{}).get("missing_fields",[])
                readable = [
                    FIELD_LABELS.get(f, f.replace("_", " ").title())
                    for f in missing]
                return ("I need a bit more information to answer this.\n""Missing details: " + ", ".join(readable))
            if result.get("has_answer")==True and result.get("meta",{}).get("status")=="ok":    
                freshness = result.get("meta", {}).get("freshness", "unknown")
                fallback_used = result.get("meta", {}).get("fallback_used", False)
                if freshness == "fresh" and not fallback_used:
                    return result["answer"]
                if relevance_map.get("link_answer", 0) > LINK_RELEVANCE_MIN:
                    reason=("api_stale" if freshness == "stale" else "api_unknown")
                    links=retrieve_live_sources(query)
                    if links:
                        return (result["answer"]+ format_live_sources(links,reason=link_reason(reason)))
            continue
        # General
        if module=="general":
            result=call_general(query,route,mode="module")
            gen_rel = relevance_map.get("general", 0)
            src_rel = relevance_map.get("live_sources", 0)
            if (src_rel > LINK_RELEVANCE_MIN and abs(gen_rel - src_rel) <= RELEVANCE_CLOSE_DELTA):
                links = retrieve_live_sources(query)
                if links:
                    return (result["answer"]+ format_live_sources(links,reason=link_reason("general_info")))
            if result.get("has_answer"):
                return result["answer"]
            continue
    # Last failsafe
    return call_general(query,route,mode="failsafe")["answer"]