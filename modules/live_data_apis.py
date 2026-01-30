#APIs
import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone, timedelta

with open("data/static_lookup/stations_lookup.json", "r", encoding="utf-8") as f:
    STATION_LOOKUP = json.load(f)
with open("data/static_lookup/trains_lookup.json", "r", encoding="utf-8") as f:
    TRAIN_LOOKUP = json.load(f)
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    raise RuntimeError("RAPIDAPI_KEY is not set")
RAPIDAPI_HOST = "irctc1.p.rapidapi.com"
BASE_URL = "https://irctc1.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}
llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
LLM_MODEL = "gpt-4.1-mini"
ENTITY_PROMPT = """
You extract structured railway-related information from user queries.

Return ONLY valid JSON.
Do NOT infer or assume missing information.
Do NOT guess defaults.
Extract a field ONLY if it is explicitly mentioned by the user.
If a value is not present, use null or an empty list as specified.

Supported intents (choose ONE):
- train_live_status              (live running status of a train)
- train_schedule                 (timetable / schedule of a train)
- trains_between_stations        (trains running between two stations)
- seat_availability              (seat/berth availability enquiry)
- fare_enquiry                   (ticket fare enquiry)
- pnr_status                     (PNR booking status)
- live_station                   (live arrivals/departures at a station)
- trains_by_station              (list of trains passing a station)
- search_train                   (search trains by name or number)
- search_station                 (search stations by name)
- unknown

JSON schema:
{
  "intent": string,

  "train_numbers": [string],        // 5-digit train numbers only
  "pnr_numbers": [string],          // 10-digit PNR numbers only

  "stations": [string],             // station names or codes exactly as mentioned

  "journey": {
    "from": string | null,          // source station name/code if explicitly mentioned
    "to": string | null             // destination station name/code if explicitly mentioned
  },

  "date": string | null,            // travel date if mentioned (keep original format)
  "class_type": string | null,      // class if mentioned (e.g., 2A, 3A, SL, CC)
  "quota": string | null,           // quota if mentioned (e.g., GN, Tatkal)
  "hours": integer | null           // time window in hours if explicitly mentioned
}

Important rules:
- Do NOT convert station names to codes.
- Do NOT normalize dates or class names.
- Do NOT infer intent from missing data.
- Do NOT fill defaults.
- If multiple values exist, extract all where applicable.
"""

def extract_with_llm(query):    
    resp = llm.chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": ENTITY_PROMPT},
            {"role": "user", "content": query}
        ]
    )
    return json.loads(resp.choices[0].message.content)

def call_api(path: str, params):
    print("\n[API CALL]")
    print("URL:", BASE_URL + path)
    print("PARAMS:", params)
    try:
        r = requests.get(
            BASE_URL + path,
            headers=HEADERS,
            params=params,
            timeout=10
        )
        print("STATUS:", r.status_code)
        print("RESPONSE:", r.text[:300])
        if r.status_code != 200:
            return None, r.headers
        return r.json().get("data"), r.headers
    except Exception as e:
        print("❌ API EXCEPTION:", e)
        return None, None

def resolve_train_number(value: str):
    if not value:
        return None
    clean = value.lower().strip()
    if clean.isdigit() and len(clean) == 5:
        return clean
    return TRAIN_LOOKUP.get(clean)
def resolve_station_code_local(name: str):
    if not name:
        return None
    clean = name.lower().strip()
    if clean in STATION_LOOKUP:
        return STATION_LOOKUP[clean]
    return resolve_station_code(name)

def resolve_station_code(name: str):
    if not name:
        return None
    clean = name.lower().replace(" station", "").strip()
    data, _ = call_api("/api/v1/searchStation", {"query": clean})
    if not data:
        return None
    for s in data:
        station_name = s.get("name", "").lower()
        if station_name == clean:
            return s.get("code")
    for s in data:
        station_name = s.get("name", "").lower()
        if station_name.startswith(clean):
            return s.get("code")
    return data[0].get("code")

# Determine freshness (for additional links)
def determine_freshness(headers):
    if not headers:
        return "unknown"    
    date_header = headers.get("Date")
    if not date_header:
        return "unknown"
    try:
        response_time = datetime.strptime(
            date_header, "%a, %d %b %Y %H:%M:%S GMT"
        ).replace(tzinfo=timezone.utc)
    except Exception:
        return "unknown"
    if datetime.now(timezone.utc) - response_time > timedelta(minutes=60):
        return "stale"
    return "fresh"

# Date format correction

def normalize_date_for_api(date_str):
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str,fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return None

#APIs

def get_train_live_status(e):
    return call_api("/api/v1/liveTrainStatus", {"trainNo": e["train_number"]})
def get_train_schedule(e):
    return call_api("/api/v1/getTrainSchedule", {"trainNo": e["train_number"]})
def get_trains_between_stations(e):
    return call_api("/api/v3/trainBetweenStations", {
        "fromStationCode": e["from_station"],
        "toStationCode": e["to_station"],
        "dateOfJourney": e["date"]
    })
def get_pnr_status(e):
    return call_api("/api/v3/getPNRStatus", {"pnrNumber": e["pnr"]})
def get_live_station(e):
    return call_api("/api/v3/getLiveStation", {
        "fromStationCode": e["station_code"],
        "hours": e.get("hours", 2)
    })
def get_trains_by_station(e):
    return call_api("/api/v3/getTrainsByStation", {"stationCode": e["station_code"]})
def search_train(e):
    return call_api("/api/v1/searchTrain", {"query": e["query"]})
def search_station(e):
    return call_api("/api/v1/searchStation", {"query": e["query"]})
def get_seat_availability(e):
    return call_api("/api/v1/checkSeatAvailability", {
        "trainNo": e["train_number"],
        "fromStationCode": e["from_station"],
        "toStationCode": e["to_station"],
        "date": e["date"],
        "classType": e["class_type"],
        "quota": e.get("quota", "GN")
    })
def get_seat_availability_v2(e):
    return call_api("/api/v2/checkSeatAvailability", {
        "trainNo": e["train_number"],
        "fromStationCode": e["from_station"],
        "toStationCode": e["to_station"],
        "date": e["date"],
        "classType": e["class_type"],
        "quota": e.get("quota", "GN")
    })
def get_fare(e):
    return call_api("/api/v1/getFare", {
        "trainNo": e["train_number"],
        "fromStationCode": e["from_station"],
        "toStationCode": e["to_station"],
        "date": e["date"],
        "classType": e["class_type"],
        "quota": e.get("quota", "GN")
    })

#Check whether apis match


# Calling crct API
# Mapping intent to API

INTENT_TO_API = {
    "train_live_status": {
        "required": ["train_number"],
        "handler": get_train_live_status,
        "fallback": "train_schedule"
    },
    "train_schedule": {
        "required": ["train_number"],
        "handler": get_train_schedule,
        "fallback": None
    },
    "trains_between_stations": {
        "required": ["from_station", "to_station", "date"],
        "handler": get_trains_between_stations,
        "fallback": None
    },
    "seat_availability": {
        "required": ["train_number", "from_station", "to_station", "date", "class_type"],
        "handler": get_seat_availability,
        "fallback": "seat_availability_v2"
    },
    "seat_availability_v2": {
        "required": ["train_number", "from_station", "to_station", "date", "class_type"],
        "handler": get_seat_availability_v2,
        "fallback": None
    },
    "fare_enquiry": {
        "required": ["train_number", "from_station", "to_station", "date", "class_type"],
        "handler": get_fare,
        "fallback": None
    },
    "pnr_status": {
        "required": ["pnr"],
        "handler": get_pnr_status,
        "fallback": None
    },
    "live_station": {
        "required": ["station_code"],
        "handler": get_live_station,
        "fallback": "trains_by_station"
    },
    "trains_by_station": {
        "required": ["station_code"],
        "handler": get_trains_by_station,
        "fallback": None
    },
    "search_train": {
        "required": ["query"],
        "handler": search_train,
        "fallback": None
    },
    "search_station": {
        "required": ["query"],
        "handler": search_station,
        "fallback": None
    }
}

# Main

def answer_with_live_data(query):
    parsed = extract_with_llm(query)
    intent = parsed.get("intent", "unknown")
    if intent not in INTENT_TO_API:
        return {"answer": None, "has_answer": False, "meta": {"status":"nothing"}}
    entity = {"query": query}
    if parsed.get("train_numbers"):
        tn = resolve_train_number(parsed["train_numbers"][0])
        if tn:
            entity["train_number"] = tn
    if parsed.get("pnr_numbers"):
        entity["pnr"] = parsed["pnr_numbers"][0]
    resolved = []
    for s in parsed.get("stations", []):
        code = resolve_station_code_local(s)
        if code:
            resolved.append(code)
    if len(resolved) == 1:
        entity["station_code"] = resolved[0]
    journey = parsed.get("journey")
    if journey and journey.get("from") and journey.get("to"):
        f = resolve_station_code_local(journey["from"])
        t = resolve_station_code_local(journey["to"])
        if f and t:
            entity["from_station"] = f
            entity["to_station"] = t
    if parsed.get("date"):
        normalized = normalize_date_for_api(parsed["date"])
        if normalized:
            entity["date"] = normalized
    elif intent == "trains_between_stations":
        entity["date"] = datetime.now(timezone.utc).strftime("%d-%m-%Y")
    for k in ["class_type", "quota", "hours"]:
        if parsed.get(k) is not None:
            entity[k] = parsed[k]
    api = INTENT_TO_API[intent]
    # required, missing
    required = api["required"]
    missing = [k for k in required if k not in entity]
    if missing:
        return {
            "answer": None,
            "has_answer": False,
            "meta": {
                "status": "need_input",
                "reason": "missing_required_fields",
                "intent": intent,
                "missing_fields": missing,
                "partial_entity": entity
            }
        }
    # Primary API call
    data, headers= api["handler"](entity)
    fallback_used = False
    # Fallback handling
    if not data and api.get("fallback"):
        fb = INTENT_TO_API[api["fallback"]]
        if all(k in entity for k in fb["required"]):
            data, headers= fb["handler"](entity)
            if data:
                fallback_used = True
    # Freshness detection (safe, signal only)
    freshness = determine_freshness(headers)
    if not data:
        return {"answer": None, "has_answer": False, "meta": {"status": "api_failed","intent": intent}}
    return {
        "answer":data,
        "has_answer": True,
        "meta": {
            "status": "ok",
            "intent": intent,
            "fallback_used": fallback_used,
            "freshness": freshness,
            "resolved": {
                "train_number": entity.get("train_number"),
                "station_code": entity.get("station_code"),
                "from_station": entity.get("from_station"),
                "to_station": entity.get("to_station"),
                "date": entity.get("date")
            }
        }
    }
#TEST
# if __name__ == "__main__":
#     print("=" * 80)
#     print("API TEST STARTED")
#     print("RAPIDAPI_KEY exists:", bool(RAPIDAPI_KEY))
#     print("RAPIDAPI_HOST:", RAPIDAPI_HOST)
#     print("=" * 80)

#     test_queries = [
#          # search station (sanity check)
#         "Kozhikode trains",
#         # search train (sanity check)
    
#     ]

#     for q in test_queries:
#         print("\n" + "-" * 60)
#         print("Query:", q)

#         result = answer_with_live_data(q)

#         print("HAS ANSWER:", result.get("has_answer"))
#         print("META:", result.get("meta"))

#         if result.get("has_answer"):
#             print("DATA PREVIEW:")
#             print(result["answer"][:500])  # prevent huge spam
#         else:
#             print("❌ NO DATA RETURNED")

#     print("\nAPI TEST COMPLETED")
