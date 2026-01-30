from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import traceback
from dotenv import load_dotenv
load_dotenv()
from Chatbot.bot import answer_query

app = FastAPI(title="Railway Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    confidence: str | None = None
    source: str | None = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        answer = answer_query(request.query)
        # Defensive fallback (never return None)
        if not answer:
            answer = "I couldn’t process that. Please try rephrasing your question."
    except Exception:
        traceback.print_exc()
        answer = "Something went wrong while processing your request."
    return {
        "answer": answer,
        "confidence": None,
        "source": None
    }

@app.get("/")
def serve_ui():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# Serve static assets (CSS, JS, images)
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)
