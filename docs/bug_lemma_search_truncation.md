# Bug: lemma search silently drops valid matches on truncation

## Summary
`lemma_search_with_context` returned an unordered `set` of matched chunk_ids and truncated it with `matched_ids[:limit]`. Since Python sets have no meaningful order, this truncation can silently discard valid matches from rare/specific query lemmas in favor of matches from common ones — with no error, no warning, and no indication that anything was lost.

## How it was found
Discovered via retrieval eval, not by chance: the query `"pain d'épices Swann"` consistently failed on the `/chat` endpoint, in a way that contradicted an earlier, related success — `"where did Swann buy gingerbread and why"` (a paraphrase of the same fact) succeeded and correctly cited chunk `ch3_p18_s4_c0`. Two phrasings of the same underlying fact behaving inconsistently was the signal that something structural — not just embedding/ranking noise — was wrong with the lexical path specifically.

## Reproduction

Query lemmas for `"pain d'épices Swann"`: `["pain", "épice", "swann"]`.

Checking the lemma index directly for the specific (rare) lemma:

```
DEBUG épice > ['ch3_p18_s4_c0']
```

Confirms the correct chunk_id is present and correctly indexed under `épice`.

Checking the final output of `lemma_search_with_context(...)` for the same query:

```
chunk_ids ['ch2_p202_s5_c0', 'ch2_p338_s8_c0', 'ch2_p213_s1_c0',
'ch1_p164_s3_c0', 'ch2_p584_s0_c0', 'ch1_p295_s5_c1', 'ch2_p533_s6_c0',
'ch3_p62_s28_c0', 'ch2_p65_s0_c0', 'ch2_p535_s5_c0', 'ch2_p408_s8_c0',
'ch2_p322_s3_c0', 'ch2_p202_s4_c0', 'ch2_p412_s6_c0', 'ch1_p18_s9_c0',
'ch1_p18_s1_c0', 'ch2_p566_s25_c0', 'ch1_p27_s1_c0', 'ch1_p162_s1_c0',
'ch2_p17_s6_c0', 'ch2_p195_s7_c0', 'ch2_p185_s0_c0', 'ch2_p531_s17_c0',
'ch2_p534_s1_c0', 'ch2_p279_s0_c0', 'ch2_p496_s1_c0', 'ch1_p197_s1_c0',
'ch2_p80_s0_c0', 'ch2_p13_s1_c0', 'ch1_p27_s10_c0', 'ch2_p410_s0_c0',
'ch1_p203_s0_c0', 'ch2_p216_s0_c0', 'ch2_p287_s3_c0', 'ch2_p328_s1_c0',
'ch2_p179_s3_c0', 'ch2_p333_s8_c0', 'ch2_p134_s10_c0', 'ch3_p63_s15_c0',
'ch2_p538_s2_c0', 'ch2_p340_s1_c0', 'ch2_p530_s3_c0', 'ch2_p17_s2_c1',
'ch2_p220_s0_c0', 'ch2_p334_s0_c0', 'ch1_p22_s8_c1', 'ch2_p383_s8_c0',
'ch1_p306_s4_c0', 'ch2_p108_s1_c0', 'ch2_p195_s2_c0']
```

`ch3_p18_s4_c0` is **not present** — 50 results returned (the `limit`), none of them the one confirmed-correct match from `épice`.

## Root cause

```python
for lemma in lemmas:
    if lemma == "épice":
        print("DEBUG", lemma, ">", lemma_index.get(lemma, []))
    matched_ids.update(lemma_index.get(lemma, []))
return list(matched_ids)[:limit]
```

`matched_ids` is correctly accumulated across lemmas via `.update()` — the union itself is not the problem. The problem is the final line: `list(matched_ids)[:limit]`.

Python sets are unordered — iteration order depends on hash values, not on insertion order, relevance, or which lemma contributed an item. `"swann"` is a common lemma with a large number of matching chunks; `"épice"` contributes exactly one. When the full union exceeds `limit` (50), the slice keeps whichever 50 items happen to come first in hash order — with no relationship to relevance. In this case, `épice`'s single, highly specific match did not survive the cut.

This means: **any query combining a common lemma with a rare/specific one is at risk of silently losing the specific match**, purely as a function of set hash ordering — not embedding distance, not chunking, not query phrasing.

## Fix options considered

1. **Minimal**: skip truncating the lemma-side union at all; let `merge_results` do the final ranking/limiting downstream.
2. **Better**: rank candidates before truncating — e.g. score each chunk_id by number of distinct query lemmas it matched (a chunk matching all 3 query lemmas is more relevant than one matching only `"swann"`), then take the top `limit` by that score.
3. **Cheap partial fix**: prioritize rarer lemmas' matches before truncating (guarantee low-frequency lemma hits survive first, then fill remaining slots with common-lemma hits).

## Fix (implemented)

Replaced the unordered `set` + arbitrary truncation with an IDF-style weighted score per chunk, computed in a single pass over the query's lemmas.

**Reasoning**: the original bug happened because presence in a `set` carries no information about *how relevant* a match is — a chunk matching one common lemma (`"swann"`, df=691) was indistinguishable from a chunk matching one rare, informative lemma (`"épice"`, df=1). The fix scores each lemma's contribution to a chunk by `1 / df`, where df is the lemma's number of occurrences in the lemma index (691 for `swann`, across 645 chunks) — a match on a rare lemma contributes far more to a chunk's score than a match on a common one, and a chunk matching multiple query lemmas accumulates score from each. Sorting by this score before truncating means the correct/most-specific chunk is never at risk of being cut, regardless of how large the union of candidates is.

**Per-lemma df** is available directly from `len(lemma_index.get(lemma, []))` at the moment each lemma's matches are fetched — no separate pass is needed to compute it.

**Repeated-mention safeguard**: each lemma's match list is deduplicated to unique chunk_ids before scoring, so a chunk mentioning "Swann" four times still contributes only one `1/df` score for that lemma — not four. Without this, the fix would silently reintroduce the original failure mode (raw mention-count drowning out rarity).

### Verified output

For `"pain d'épices Swann"` (lemmas: `pain`, `épice`, `swann`; df=7, 1, 691 respectively), scored and sorted (first 10 of 50 shown):

```
[('ch3_p18_s4_c0', 1.1443043208600372),
 ('ch2_p19_s3_c0', 0.14285714285714285),
 ('ch1_p353_s4_c0', 0.14285714285714285),
 ('ch1_p349_s1_c0', 0.14285714285714285),
 ('ch1_p111_s4_c0', 0.14285714285714285),
 ('ch3_p60_s4_c0', 0.14285714285714285),
 ('ch1_p53_s3_c1', 0.14285714285714285),
 ('ch2_p413_s1_c0', 0.001447178002894356),
 ('ch2_p45_s13_c0', 0.001447178002894356),
 ('ch2_p198_s1_c0', 0.001447178002894356)]
```

`ch3_p18_s4_c0` (matching all three lemmas: `1 + 1/7 + 1/691 ≈ 1.144`) is now correctly ranked first — no longer at risk of being dropped by an unordered-set truncation. Chunks matching only `"pain"` (df=7) form the next tier at `1/7 ≈ 0.143`; chunks matching only `"swann"` (df=691) fall to the bottom at `1/691 ≈ 0.0014`, as intended.

Later change: only chunks matching at least one rare lemma (at or below the frequency threshold) enter the list; common lemmas still add their score to those chunks, so they affect the order but never add chunks. This removed the chunks matching only common lemmas (the `swann` tier at the bottom of the output above, which filled the remaining slots of the 50-result list) while keeping common words as tie-breakers: q06 improved from rank 3 to 2.

### Known limitation of this fix

For single-lemma queries (e.g. a bare `"madeleine"`), every matching chunk ties at the same score — there's no second signal to break the tie, since all matches share the same (and only) lemma's `1/df` weight. This fix improves ranking specifically for multi-lemma queries where lemma rarity varies; it does not add new ordering information for single-lemma queries.
This tie is also why MRR varies between eval runs: tied chunks are ordered by hash-random set iteration (see the MRR note in [eval_and_bugs.md](eval_and_bugs.md), and q17).

### Verification
- `q08` ("pain d'épices Swann") passes end-to-end, both in the eval harness and via `/chat`. Also covered by `test_lemma_search` in `test_lemma_search.py`.
- Full eval re-run after the fix: `q11` (Françoise) still misses, for a reason documented separately: "Françoise" is too common to trigger lemma search at all (see finding 4 in [eval_and_bugs.md](eval_and_bugs.md)).