
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

Cmd + Shift + E to search for paths

```sh
uvicorn main:app --reload
```

