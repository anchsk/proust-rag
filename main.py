from typing import Annotated
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from search import retrieve, search_db, settings
from chat import prepare_prompt, generate
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints
from lang import detect_language

QueryStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class QueryRequest(BaseModel):
    query: QueryStr


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
def search(request: QueryRequest):
    results = search_db(request.query, limit=settings.db_limit)
    return results


@app.post("/chat")
def chat(request: QueryRequest):
    results = retrieve(request.query)
    if not results:
        return {"message": "No relevant passages found."}

    prompt = prepare_prompt(request.query, results)
    lang_detected = detect_language(request.query)
    answer = generate(prompt, lang_detected)

    return StreamingResponse(answer, media_type="text/event-stream")

