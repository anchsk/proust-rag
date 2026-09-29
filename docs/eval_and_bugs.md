# Retrieval evaluation and findings

## What this is

`eval_set.json` is a list of test questions, each paired with the chunk
ID(s) of the passage(s) that should be retrieved to answer it correctly.
The questions were built by hand: some are famous, easily recognizable
scenes from the book (the madeleine, the first sight of Gilberte — the
mother's-goodnight-kiss scene is still to be added). Others were built by
searching the source CSVs directly, or by querying the lemma index and the
semantic search separately, to find passages that would make good, clearly
answerable test cases.

The set is still small (16 queries at time of writing) and is expected to
grow.

## What is being tested

Each query is run through the same steps the `/chat` endpoint uses,
stopping right before the final step of sending the retrieved passages to
the language model (Claude, via the Anthropic API):

```py
classify_intent()
search_db()
lemma_search_with_context()
merge_results()
chunk_id_list = [r["meta"]["chunk_id"] for r in results]
```

This tests retrieval in isolation — did the system find the right passages
— separately from whether the language model then writes a good answer
from them. The two are different questions; keeping them separate makes it
possible to say clearly "retrieval found it" versus "retrieval found it but
the answer was still wrong" (see the Françoise/hallucination note below).

## Query types

Each query is tagged with a `type`, to help spot patterns rather than just
reading one blended score:

- **semantic** — the query is phrased naturally (a paraphrase or
  description) and is expected to be found through vector similarity
  (i.e. "does this passage mean something close to what was asked"),
  rather than by matching exact words.
- **lexical** — the query is expected to succeed because it contains a
  specific, identifiable word or name that exists in the lemma index (an
  index of word roots, used for exact-term lookups the semantic search can
  miss).
- **cross-lingual** — the query is in a different language than the
  source text (French). The embedding model used is multilingual, so this
  checks whether it can match meaning across languages.
- **negative** — the query asks about something that does not appear in
  the text at all. The correct result is no relevant passages returned.
  Since retrieval has no distance threshold, it always returns 5 chunks, so
  a negative query always shows as FAIL at the retrieval level; the real
  check is whether the generated answer says the text doesn't cover it.

One overlap worth naming honestly: a query can belong to more than one type
at once. An English-language query is technically cross-lingual too, since
the source text is French — the type tags describe what a query is
*primarily* testing, not a strict, non-overlapping category. It's also
possible for a query labeled one type to actually exercise another type's
code path — e.g. a `semantic`-labeled query that happens to contain a rare
proper noun will still trigger the lemma-search path via `classify_intent`,
even though "lexical" isn't its primary label (see the MRR note below for a
concrete case of this).

## Metrics

Three metrics are calculated for the non-negative ("positive") queries:

- **Recall (hit rate)**: for a given query, did *at least one* correct
  chunk appear anywhere in the results? Scored 1 (yes) or 0 (no) per query,
  then averaged. This is technically "hit rate," not textbook recall —
  textbook recall would ask what *fraction* of all correct chunks were
  found, which is what "coverage" (below) measures instead. For queries
  with only one correct chunk, the two are identical; the difference only
  shows up on multi-answer queries.
- **Coverage**: for queries with more than one correct chunk (e.g. "is
  there any mention of snow," which has five valid passages), this measures
  what fraction of them were actually retrieved — not just whether any one
  of them was.
- **MRR (Mean Reciprocal Rank)**: measures *where* the first correct chunk
  appeared in the results, not just whether it appeared. A correct chunk in
  first place scores 1.0; in fifth place, 0.2. This distinguishes "found it
  immediately" from "found it, but buried far down the list."

The negative-case query is scored separately, as a simple PASS/FAIL (did
the system correctly return nothing, or did it return unrelated results
anyway) — it isn't combined into the recall/MRR/coverage numbers, since it's
answering a different question ("does it know when to say nothing") than
the others ("how well does it rank the right answer").

## Results

```shell
type             n   recall        mrr   coverage
---------------------------------------------------
cross-lingual    3    0.667      0.667      0.667
lexical          2    0.500      0.500      0.500
semantic        10    0.500      0.275      0.440
---------------------------------------------------
overall         15    0.533      0.383      0.493
```

These numbers include q14 (Vermeer) as a semantic query for the first time;
it was previously the negative case (see finding 7). It's a known miss, so
part of the drop in semantic recall compared with earlier runs comes from
this relabeling, not from the system getting worse. The MRR values are a
single run; see the note below on why MRR varies between runs.

Negative case (q16 — a query about Picasso, who does not appear in the
text): **FAIL** at the retrieval level, as expected (see Query types); the
generated answer correctly said the text doesn't mention him. See
[finding_negative_case_no_threshold.md](finding_negative_case_no_threshold.md)
for details.

**Why MRR varies between runs.**
Re-running the harness multiple times with no code changes produces
different semantic/overall MRR each time (observed: 0.183, 0.332, 0.341,
0.393 across four consecutive runs) while recall and coverage stay exactly
fixed. This isn't measurement noise or a bug in the harness — it's a real,
already-tracked property of `lemma_search`: for a single-lemma query, every
matching chunk ties at the same score, and Python's hash-randomized set
iteration order (different every process run, by design) decides which tied
chunk lands first. So *whether* the right passage is found is stable
(recall/coverage), but *where it ranks* among ties isn't (MRR). This is why
it shows up under "semantic" specifically: `q05` ("how does he describe the
sensation of eating madeleines") is labeled `semantic` but contains the
rare lemma "madeleines," so it still runs through the lemma path where the
tie-breaking lives. See `TODO.md` (search.py section) for this item. Treat
any single MRR figure quoted elsewhere for this eval set as one sample from
that range, not a fixed ground truth.

**Caveat on the numbers above**: lexical still has only 2 queries — at that
size a single query changing outcome swings the group average by 50%.
Cross-lingual grew from 2 to 3 with the addition of q15 (see finding 4a
below), still small but slightly less fragile than before. Semantic, at 10
queries, remains the most informative, though still small in absolute
terms.

## Key findings

**1. Lemma search was silently dropping correct results (fixed).**
A bug in `lemma_search` caused it to discard a valid, correct match when a
query combined a rare term with a common one (e.g. "pain d'épices Swann" —
"Swann" appears in hundreds of chunks, drowning out the rare, correct match
on "épices"). Root cause, evidence, and fix are documented in
[bug_lemma_search_truncation.md](bug_lemma_search_truncation.md).

**2. Separately from the bug above: long, multi-topic sentences rank lower
in semantic search, even when correctly chunked.**
The same query used to find the lemma bug also showed a second, unrelated
problem: even after the lemma-side bug was fixed, the semantic-search path
alone still ranked the correct passage low (9th place, not in the top 5).
The likely reason is that the sentence covers several sub-topics at once
(a merchant's stall, the purchase, Swann's digestion, two children) — the
embedding for the whole sentence reflects all of that mixed content, not
just the one detail the query asked about. This is a separate, still-open
observation from the lemma bug: fixing the bug meant this query now
succeeds via the lemma path instead, but the semantic-ranking weakness
itself hasn't been changed or fixed.

**3. Abstract or relational questions about a character are harder to
retrieve than concrete, descriptive ones — regardless of language.**
A query asking how Odette is described "as an adult" failed to retrieve a
correct passage, while a very similar query asking specifically how she
*dressed* succeeded, retrieving multiple correct passages. An earlier
theory was that this was caused by the text referring to her as "Mme
Swann" once she is married, rather than "Odette" (the name used in the
queries) — but this was tested directly and ruled out: the concrete
clothing query, still using "Odette," successfully retrieved a passage that
refers to her as "Mme Swann." The naming difference did not block
retrieval. The pattern that remains, tested in both Russian and French, is:
concrete/descriptive queries succeed more reliably than abstract or
relational ones about the same character.

**4. Common characters have no fallback when semantic search misses them
(confirmed cause).**
Two queries about the narrator's feelings toward specific characters
("what does the narrator feel about Françoise," "who did the narrator fall
in love with") failed to retrieve the correct passage. Checking
`classify_intent`'s code confirmed why: it only enables the lemma-index
fallback when a query contains a *rare* term (appearing in 50 or fewer
chunks). Françoise is mentioned 171 times, so she is correctly excluded —
`classify_intent` is working exactly as designed, not misbehaving.

This means the lemma fallback — the system's only backup when semantic
search doesn't find the right passage — is specifically built to skip the
most-mentioned characters, which are also the characters people are most
likely to ask about. Combined with finding 3 above (semantic search
struggles with abstract/relational questions about a character), this
leaves a gap: an abstract question about a common character has no second
path to fall back on if semantic search misses it.

A further check on this query surfaced a second, separate point, described
below.

**4a. Distance scores are not comparable across different queries.**
Two test queries about Françoise were compared directly:

- *"what does the narrator feel about Françoise?"* — returned chunks with
  distances 0.245-0.319, but none of them were actually relevant to the
  question (they were unrelated dialogue fragments).
- *"cosa cucinava Françoise?"* ("what did Françoise cook?", in Italian) —
  returned a correct, relevant match at distance 0.257, with the rest of
  the list in a similar 0.26-0.35 range. This query is now formalized as
  **q15** in `eval_set.json` (cross-lingual, expected `ch1_p261_s0_c0`) —
  previously it was only checked ad hoc, not tracked in the eval set. It's
  also locked in separately as a regression test in `test_search.py`.

The two result sets have almost identical distance ranges, even though one
is a clear miss and the other is a good match. This means a chunk's
distance score cannot be read on its own as "this is a good match" or "this
is a bad match" — the same numeric range can mean either, depending on the
query. This reinforces finding 5 below (the negative-case result), and adds
to it: the problem isn't only that irrelevant results can score as low
(close) as relevant ones for a single query — the *whole scale* of what
counts as "close" appears to shift from query to query, which would make
any single, fixed distance threshold applied across all queries
unreliable.

**5. Retrieval always returns results, even when nothing relevant exists,
and distance scores don't clearly separate good matches from bad ones.**
See [finding_negative_case_no_threshold.md](finding_negative_case_no_threshold.md).

**6. Separate from retrieval: the language-generation step has produced at
least one fabricated quote.**
While checking a retrieval result for the Françoise query, one generated
answer included a quote in quotation marks that does not appear anywhere in
the source text, and mis-cited a paragraph number for a real quote. This is
a generation-quality issue, not a retrieval issue — the passages retrieved
appeared correct; what the model wrote about them was not fully accurate.
Worth tracking separately as its own concern going forward.

**7. Names contribute almost nothing to semantic search; the words around
them decide the result.**
q14 (*"What does the narrator say about the painter Vermeer?"*) was
originally the negative case, until it turned out Vermeer does appear, in
ch.2, spelled the way Proust writes it: "Ver Meer" (e.g. `ch2_p533_s2_c0`).
Checking why the system missed it:

- Semantic search alone (`/search`) with the bare name "vermeer" returns
  short, unrelated exclamations ("Verdurin!", "Brava!"). The name gives the
  embedding almost nothing to work with, and very short clauses like these
  seem to sit close to many weak queries.
- With the full q14 question, semantic search returns sentences containing
  *peintre*. A Ver Meer chunk appears at rank 10 (k=20), but only because
  it also contains "peintre": it competes with every other sentence about
  a painter and falls outside the top 5.
- Lemma search can't rescue it: the text has "Ver" + "Meer", and there is
  no lemma "vermeer".
- With Proust's spelling it works: "ver meer de Delft" through `/chat`
  finds the Ver Meer passages via lemma search, while "ver meer" through
  `/search` (semantic only) returns unrelated results ("bigre!", at
  distance 0.29).

The new negative case, q16 (Picasso), shows the same effect: all five
returned sentences contain *peintre*. Possible fixes, not built: an alias
map for historical spellings (Vermeer → Ver Meer), or also indexing the
lowercase joined form of consecutive proper nouns ("vermeer").

## Known limitations and next steps

- **Dataset size.** 16 queries is enough to find real, specific bugs
  (as it did) but too small for the aggregate numbers to be a stable
  measure of overall system quality. Expanding toward 25-30 queries,
  especially for lexical (currently 2) and cross-lingual (now 3, still thin),
  is the clearest next step before treating these scores as meaningful over
  time.
- **MRR is not currently a stable metric for this eval set**, independent of
  dataset size — see the note under Results. Fixing this (e.g. breaking ties
  by something other than hash-random set order in `lemma_search`) would
  need to happen before MRR trends over time can be trusted; recall and
  coverage aren't affected and are safe to compare across runs today.
- **Negative-case coverage.** Only one negative query exists so far
  (q16, Picasso; the original one, Vermeer, turned out not to be negative,
  see finding 7). Whether irrelevant results typically score in the same
  range as relevant ones (0.29-0.36 in the Vermeer run) is unknown until
  more negative cases are tested.
- **Open findings not yet resolved**: items 2 and 3 above are documented
  observations, not fixed bugs — they need further investigation before any
  fix is attempted. Item 4 has a confirmed root cause (see above) but no
  fix designed yet — a fix would mean deciding how to catch abstract
  queries about common characters, which is a design question (what should
  trigger a fallback, if not rarity?) rather than a simple code correction.
- **Distance thresholds are not a safe fix on their own** (findings 4a and
  5): before adding any cutoff based on distance score, it should be tested
  against a wider range of both relevant and irrelevant queries, since the
  same distance range has been shown to mean different things depending on
  the query.