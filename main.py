import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, StreamingResponse
from search import retrieve, search_db, settings
from chat import prepare_prompt, generate
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, StringConstraints
from lang import detect_language

load_dotenv(".env.prod")

QueryStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class QueryRequest(BaseModel):
    query: QueryStr


description = """
Question answering over Proust's *Du côté de chez Swann*, with hybrid (semantic + exact-term) retrieval and answers from Claude.
Try `/search` to see raw retrieval, or `/chat` for a full answer.

- Source code: [github.com/anchsk/proust-rag](https://github.com/anchsk/proust-rag)
- Frontend: [proust-app.vercel.app](https://proust-app.vercel.app)
- Evaluation and findings: [docs/](https://github.com/anchsk/proust-rag/tree/main/docs)
"""

app = FastAPI(
    title="proust-rag",
    description=description,
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},  # hide the Schemas block
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


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

