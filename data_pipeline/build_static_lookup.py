import json
from pathlib import Path

INP_DIR = Path("data/raw_docs/train_station")
OUT_DIR = Path("data/static_lookup")
OUT_DIR.mkdir(parents=True, exist_ok=True)

train_lookup = {}
station_lookup = {}

STATION_EXPANSIONS = {
    " JN": " JUNCTION"
}
TRAIN_EXPANSIONS = {
    " SF ": " SUPERFAST ",
    " EXP ": " EXPRESS ",
    " E ": " EXPRESS ",
    " SPL ": " SPECIAL "
}

def normalize(text: str) -> str:
    return " ".join(text.upper().split())

def expand_all(name: str, expansions: dict) -> str:
    expanded = f" {name} "
    changed = True
    while changed:
        changed = False
        for short, full in expansions.items():
            if short in expanded:
                expanded = expanded.replace(short, full)
                changed = True

    return normalize(expanded)

def split_station(station_str):
    if not station_str or "-" not in station_str:
        return None, None
    name, code = station_str.rsplit("-", 1)
    return normalize(name), code.strip().upper()

for file in INP_DIR.glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        records = json.load(f)
    for r in records:
        tn = r.get("trainNumber")
        tname = r.get("trainName")
        if tn and tname:
            original = normalize(tname)
            expanded = expand_all(original, TRAIN_EXPANSIONS)
            train_lookup[original.lower()] = tn
            if expanded != original:
                train_lookup[expanded.lower()] = tn
        for stop in r.get("trainRoute", []):
            raw = stop.get("stationName")
            name, code = split_station(raw)
            if name and code:
                expanded = expand_all(name, STATION_EXPANSIONS)
                station_lookup[name.lower()] = code
                if expanded != name:
                    station_lookup[expanded.lower()] = code

with open(OUT_DIR / "trains_lookup.json", "w", encoding="utf-8") as f:
    json.dump(train_lookup, f, indent=2, ensure_ascii=False)

with open(OUT_DIR / "stations_lookup.json", "w", encoding="utf-8") as f:
    json.dump(station_lookup, f, indent=2, ensure_ascii=False)

print("✅ Static lookup files created")
print("Trains:", len(train_lookup))
print("Stations:", len(station_lookup))
