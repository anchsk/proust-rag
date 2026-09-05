from fastapi import FastAPI
from search import search as searchdb
from chat import send_prompt, prepare_prompt

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, world!"}


# http://127.0.0.1:8000/docs
@app.post("/search")
async def search(query: str):
    results = searchdb(query, n_results=5)
    return results

@app.post("/chat")
async def chat(query:str):
    results = searchdb(query)
    # build a prompt
    prompt = prepare_prompt(query, results)
    # send a prompt to chat
    if not prompt:
        return {"message": "missing prompt"}
    answer = send_prompt(prompt)
    # return answer
    return answer
    
    