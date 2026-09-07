from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from search import search_db
from chat import prepare_prompt, generate
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from lang import detect_language


class SearchRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    query: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Hello, world!"}


# http://127.0.0.1:8000/docs
@app.post("/search")
async def search(request: SearchRequest):
    results = search_db(request.query, n_results=5)
    return results


@app.post("/chat")
async def chat(request: ChatRequest):
    results = search_db(request.query)

    prompt = prepare_prompt(request.query, results)
    lang_detected = detect_language(request.query)

    if not prompt:
        return {"message": "missing prompt"}
    answer = generate(prompt, lang_detected)

    return StreamingResponse(answer, media_type="text/event-stream")
