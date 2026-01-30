# Link only module
from helpers.live_sources import retrieve_live_sources
from helpers.live_sources import retrieve_live_sources
def run(query, num_of_links):
    sources = retrieve_live_sources(query, top_k=num_of_links)
    if not sources:
        return []
    return [
        {
            "url": s["url"],
            "authority": s.get("authority"),
            "similarity": s.get("similarity")
        }
        for s in sources
        if s.get("url")
    ]