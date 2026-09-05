from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from search import search as searchdb
from chat import send_prompt, prepare_prompt, generate
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
async def search(query: str):
    results = searchdb(query, n_results=5)
    return results


@app.post("/chat")
# async def chat(query:str):
#     results = searchdb(query)
#     # build a prompt
#     prompt = prepare_prompt(query, results)
#     # send a prompt to chat
#     if not prompt:
#         return {"message": "missing prompt"}
#     answer = send_prompt(prompt)
#     # return answer
#     return answer
async def chat(request: ChatRequest):
    results = searchdb(request.query)

    prompt = prepare_prompt(request.query, results)

    if not prompt:
        return {"message": "missing prompt"}
    answer = generate(prompt)

    return StreamingResponse(answer, media_type="text/event-stream")
