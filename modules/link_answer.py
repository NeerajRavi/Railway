# Link only module
from helpers.live_sources import retrieve_live_sources
# def run(query,num_of_links):
#     sources = retrieve_live_sources(query, top_k=num_of_links)
#     if not sources:
#         return {
#             "answer": None,
#             "has_answer": False,
#             "meta": {}
#         }
#     links = [s["url"] for s in sources if s.get("url")]
#     if not links:
#         return {
#             "answer": None,
#             "has_answer": False,
#             "meta": {}
#         }
#     return {
#         "answer": links,        
#         "has_answer": True,
#         "meta": {
#             "type": "links_only",
#             "requested_count": num_of_links,
#             "returned_count": len(links),
#             "sources": [
#                 {
#                     "url": s["url"],
#                     "authority": s.get("authority"),
#                     "similarity": s.get("similarity")
#                 }
#                 for s in sources
#             ]
#         }
#     }
# Link only module
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