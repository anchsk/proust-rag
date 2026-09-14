# eval and bugs

## What was tested

The `eval_set.json` is a list of possible questions with the ids of chunks of text that are expected. The examples are curated through trial and error. There are a lot of important passages in the book. I tried to include the questions with questions that might be known to the readers, the famous scene of madeleine, the mother's kiss (to add!), the first love of the character. Question were reformulated, keywords were searched for manually in the csv files, querying the lemma layer and search db, etc. (rewrite this sentence)
The set is small at the moment of writing. 

The set has 14 queries of 2 types:
positive cases types:
- cross-lingual
The embeddings for the text (corpus? book?) were made with multilingual model. The query can be in any language. Here it's tested against (russian, italian, engligh, french) (here i thinks it's a typology that can overlap with lexical and semantic? maybe worth clarifying? english questions are also cross-lingual in the context of the French text)
- lexical 
When the rare terms are found in the query and it's expected that the results come from the list of lemmas and not from the semantic search. It can miss specific keywords.
- semantic
Impressionist questions that look for vector proximity of the sentence more than for an exact word.
and a negative case type:
to test when the query should not return anything because the term is not present in the text.

The goal is to check the retrieved chunks of text before sending them to the chat API (in this case anthropic).

The method is to run each query in the set through the same pipeline as /chat route would do minus sending the prompt to the chat API.

The steps are: 
```py
classify_intent()
search_db()
lemma_search_with_context()
merge_results()
chunk_id_list = [r["meta"]["chunk_id"] for r in results]
return chunk_id_list
```
On top of that, we have three metrics:
recall
mrr
coverage

These metrics are calculated only for the positive cases.
The negative case only return PASS or FAIL.
The results are in the table below.

The process of evaluation generated several concerns.


## Results table

```shell
type             n   recall      mrr   coverage
-----------------------------------------------
cross-lingual    2    0.500    0.500      0.500
lexical          2    0.500    0.500      0.500
semantic         9    0.556    0.266      0.489
-----------------------------------------------
overall         13    0.538    0.338      0.492
```

## Key findings

- the lemma-truncation bug + fix
see [bug_lemma_search_truncation_upd.md](docs/bug_lemma_search_truncation_upd.md)

- semantic ranking underperforming on multi-topic chunks (q08's original symptom)
isn't it a part of the above thing?

- abstract-vs-concrete query gap (Odette), open questions (q11/q12 misses, still unexplained)
should do a write up as with the truncation bug?

## Known limitations and next steps

- dataset size caveat
- negative-control TODO ? don't we have it already?
- per-type sample sizes (they are small, but it's a part of a dataset size caveat issue, no?)