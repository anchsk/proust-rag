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

A small web service for asking questions about Proust's *Du côté de chez Swann* (*Swann's Way*, the first volume of *À la recherche du temps perdu*, in the original French) and getting answers grounded in the actual text — not the model's general knowledge of the novel.

You send it a question, it finds the passages most likely to answer it, and asks Claude to write an answer using only those passages.

## Try asking things like

- "How does he describe the church in Balbec?"
- "Where did Swann buy gingerbread, and why?"
- "What does the narrator feel about Françoise?" (a good example of a case that currently doesn't work well — see Known Limitations)

## What it does

The service exposes two endpoints:

- **`POST /search`** — a debug endpoint. Runs semantic (meaning-based) search only and returns the matching passages, without generating an answer. Useful for checking what the search is actually finding.
- **`POST /chat`** — the real endpoint. Finds relevant passages, sends them to Claude along with your question, and streams back a written answer.

The service is deployed on [Hugging Face Spaces](https://huggingface.co/spaces) as a Docker container.

## How it finds passages

There are two different ways the service looks for relevant text, and depending on the question, it uses one or both.

**Semantic search** looks for passages whose *meaning* is close to the question, using text embeddings — so it can match a paraphrase or description even if the exact words differ (e.g. "how are the flowers described" doesn't need the word "flowers" to appear). This always runs, for every question.

**Lemma (exact-term) search** looks for passages containing a specific word, in its root form — so a search for "madeleine" will find every occurrence of that word, not just the ones that happen to be semantically close to your phrasing. This only runs *sometimes* — see below.

A merge step then combines the results from both searches into one list, removing duplicates, before handing them to Claude.

### Deciding whether to use exact-term search

Before searching, the service checks your question for any word that is *specific* — meaning it shows up fairly rarely across the whole text (50 times or fewer). If it finds one, it treats the question as needing an exact match and runs the exact-term search in addition to semantic search. If every word in your question is too common to be a useful exact match (e.g. "Françoise," who's mentioned constantly), it skips that step and relies on semantic search alone.

In practice: a specific, less-common word or name tends to get more precise results; a broader or more common question relies on meaning-based matching alone — which is also where most of the known weak spots currently are (see Known Limitations).

## Why it works this way

The two-part search (semantic + exact-term) wasn't the original design — it came out of a real problem found while testing. Searching for "madeleine" itself — the single most famous word in this book — returned nothing relevant. The passage was indexed correctly, but a single word like that doesn't carry enough meaning on its own for a similarity-based search to recognize it as significant; the model compares overall meaning, not exact wording, so a short, specific query can end up "far" in meaning-space from the very passage that contains it word-for-word. That's a known, general limitation of this kind of search, not a bug in this project specifically. The fix was to add a second, exact-word-matching layer alongside the meaning-based one, so specific terms can still be found reliably even when semantic search misses them. The full investigation, with the actual numbers, is in [docs/madeleine_problem.md](docs/madeleine_problem.md).

A later case shows the same thing from the other side. Proust writes the painter's name as "Ver Meer". Asking for "ver meer" through `/search` (semantic only) returns unrelated passages, while a query with the same spelling through `/chat` finds the Ver Meer passages, because the exact-term search matches the words directly. See finding 7 in [docs/eval_and_bugs.md](docs/eval_and_bugs.md).

## Answer generation

Once passages are found, they're assembled into a prompt and sent to Claude (Anthropic's Haiku model — `claude-haiku-4-5-20251001` — chosen to keep response costs down) along with your question. The answer is streamed back as it's generated, rather than waiting for the full response.

## Stack

- **FastAPI** — web framework, serves `/search` and `/chat`
- **ChromaDB** — vector database for semantic search
- **sentence-transformers** (`paraphrase-multilingual-MiniLM-L12-v2`) — multilingual embedding model, so questions in other languages can match the French text by meaning (tested with English, Italian and Russian). Exact-term search uses a French model, so it only helps with French words and names. Short queries may be answered in the wrong language (see [finding_language_detection_short_queries.md](docs/finding_language_detection_short_queries.md)).
- **spaCy** (`fr_core_news_lg`) — French lemma extraction for exact-term search
- **Anthropic API** (`claude-haiku-4-5-20251001`) — answer generation
- **Docker** — containerized deployment
- **Hugging Face Spaces** — hosting

## Running it locally

You'll need Python 3.11, and the data files the service expects to already exist: a Chroma vector database folder (`chroma_db/`) and two CSVs under `data/` (`lemma_index.csv` and `proust_chunks_merged.csv`). These are pre-processed ahead of time — this repo doesn't build them.

You'll also need an Anthropic API key, since answers are generated by Claude. Create a file named `.env.prod` in the project root with:

```
ANTHROPIC_API_KEY=your-key-here
```

Then, to set up and run:

```sh
pyenv local 3.11.3
pyenv exec python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

```sh
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

## Deployment

The project runs as a Docker container on Hugging Face Spaces. The Dockerfile installs all dependencies — including the French language model used for the exact-term search — and starts the service with `uvicorn` on port 8000, which is what Hugging Face expects.

## Known limitations

Retrieval quality has been checked against a small, hand-built set of test questions, which has surfaced some real, concrete issues — some already fixed, some still open. Full write-ups live in [`docs/`](docs/):

- [**eval_and_bugs.md**](docs/eval_and_bugs.md) — how the evaluation works, what it measures, and the results so far.
- [**bug_lemma_search_truncation.md**](docs/bug_lemma_search_truncation.md) — a bug (now fixed) where exact-term search could silently drop a correct result.
- [**finding_negative_case_no_threshold.md**](docs/finding_negative_case_no_threshold.md) — an open issue: the service currently always returns some passages, even for questions about things that don't appear in the text at all.
- [**finding_language_detection_short_queries.md**](docs/finding_language_detection_short_queries.md) — an open issue: detecting what language a short question is written in isn't always reliable, which can affect what language Claude answers in.
- [**madeleine_problem.md**](docs/madeleine_problem.md) — the investigation that led to adding exact-term search in the first place (see "Why it works this way" above).

A few smaller, specific limitations that don't have their own write-up yet, but are worth knowing:

- **Multi-word names aren't treated as one term.** "Mme Swann" is broken into two separate words for exact-term search, not kept together — since "Swann" alone is too common to count as a specific term, this falls back to semantic search even for a name that, as a whole phrase, is fairly specific.
- **Names in historical spelling aren't matched from their modern form.** Proust writes "Ver Meer", so a question about "Vermeer" misses those passages: the name adds almost nothing to semantic search, and there is no exact-term match for "vermeer". Asking with Proust's spelling works. See finding 7 in [eval_and_bugs.md](docs/eval_and_bugs.md).
- **Broad, category-style questions aren't supported** (e.g. "list every flower mentioned in the book"). Exact-term search only looks up one specific word at a time — it has no idea that "rose," "lilac," and "violet" all belong to the same category.
- **Questions about counting or relationships across the book aren't supported** (e.g. "how many times does the narrator visit his grandmother"). That would need the system to track people, places, and events across the whole text, which is well beyond what either search method does today.
- **Exact-term search covers nouns and names only.** Verbs and adjectives rely on semantic search.

This is a project I'm actively learning from and improving — if something looks off, it's very possibly a known limitation already listed above, or on its way to being one.