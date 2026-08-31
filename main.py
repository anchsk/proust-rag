from fastapi import FastAPI
from search import search as searchdb


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World!"}


# http://127.0.0.1:8000/docs
@app.post("/search")
async def search(query: str):
    results = searchdb(query)
    return results
