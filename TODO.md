# search.py
- expand eval step (add more test cases)
+ add RAG eval step
    - retrieval quality: search_db returns the right passages for a query
- reindex with metadata
- translate query to french before doing lemma search
+ implement intent classification
- optimize query context fetch
+ add language detection
+ get SSE (Server-Sent Events) working
+ fix window mismatch main.py:43 and main.py:47
- lemma_search: single-lemma queries (e.g. "madeleine") tie-break by hash-random set order, so result ordering isn't stable across process restarts (retrieval set itself is correct/stable, only order varies)

# lang.py
- improve language detection accuracy on short queries (langdetect misdetects e.g. "how does he describe madeleines" as es/nl/pt) — see docs/finding_language_detection_short_queries.md


## notes to self:
Almost done:
language detection (quick fix) → RAG eval (cheap, high signal) → metadata reindexing (foundation) → intent classification (built on top of that foundation)
Important:
metadata reindexing (?) why? what i wanted to do?



{"question": "How does he describe the church in Balbec?", "chunk_id": "ch3_p2_s3_c0"}
{"question": "Odette et Swann s'embrassent", "chunk_id": "ch2_p180_s1_c0"}