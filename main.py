from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from search import lemma_search_with_context, merge_results, search_db, classify_intent, settings
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
    results = search_db(request.query, limit=settings["db_limit"])
    return results


@app.post("/chat")
async def chat(request: ChatRequest):
    intent = classify_intent(request.query, freq_threshold=settings["freq_threshold"])
    semantic_results = search_db(request.query, limit=settings["db_limit"])
    
    lemma_results = []
    if intent == "both":
        lemma_results = lemma_search_with_context(request.query, window=0, limit=settings["lemma_limit"])
    
    results = merge_results(lemma_results, semantic_results)
    prompt = prepare_prompt(request.query, results)
    lang_detected = detect_language(request.query)

    if not prompt:
        return {"message": "missing prompt"}
    answer = generate(prompt, lang_detected)

    return StreamingResponse(answer, media_type="text/event-stream")

