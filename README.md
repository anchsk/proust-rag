
---
title: proust-rag
emoji: 📚
colorFrom: pink
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# proust-rag

Stack: FastAPI + ChromaDB

How to run locally:

```sh
pyenv local 3.11.3
pyenv exec python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

```sh
uvicorn main:app --reload
```


## Observations after the first run

Questions like "list all authors mentioned in this book" doesn't give a good result
Vector similarity search fails (why?)

Semantic search for questions like "what did Françoise cook" works ok. It returns top-5 closest matches. I can't do exhaustive retrieval with this setup. I need to add lemma extraction or more metadata (keywords) to each chunk of text.


Ask about scenes, feelings, and passages — not exhaustive lists or exact word searches.
