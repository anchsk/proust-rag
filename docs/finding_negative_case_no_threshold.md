# Finding: the system always returns results, even when there's nothing relevant

## Summary
There's no way for the system to say "I don't have an answer to this." Semantic search always hands back its 5 closest matches, even for a question about something that isn't in the text at all. And the distance scores on those bad matches don't look meaningfully different from the scores on good matches. So, just cutting off results past a certain distance isn't a clean fix.

## Correction: the original test case wasn't a negative case
This finding was first based on q14, *"What does the narrator say about the painter Vermeer?"*, on the assumption that Vermeer doesn't appear in *Du côté de chez Swann*. That assumption was wrong. He does appear, in *Un amour de Swann* (ch.2), spelled the way Proust spells it: "Ver Meer". A text search for "Vermeer" found nothing, which is why the mistake went unnoticed.

q14 is now tracked as a regular semantic query with a known failure (see [eval_and_bugs.md](eval_and_bugs.md), finding 7). A new negative case, q16 (Picasso), replaces it.

The Vermeer run still supports the main point of this finding, for a slightly different reason: none of the five chunks it returned were the Ver Meer passages, yet they scored 0.29-0.36, the same range as results confirmed correct elsewhere. So it remains an example of wrong results looking just as "close" as right ones.

## Test case
Query (q16): *"What does the narrator say about the painter Picasso?"*
Picasso doesn't appear anywhere in the text (checked by searching the source file).

What should happen: no chunks returned, or some clear signal that nothing relevant was found.

What actually happened:
```
q16: FAIL: returned ['ch2_p45_s10_c0', 'ch2_p156_s1_c0', 'ch2_p293_s1_c0', 'ch2_p341_s0_c0', 'ch1_p106_s1_c0']
```
Distances: [0.37, 0.39, 0.40, 0.42, 0.42]

All five returned sentences contain the word *peintre* (for example, Mme Verdurin addressing the painter Biche, or a painter copying a stained-glass window in the Combray church). The name "Picasso" adds almost nothing to the query's embedding, so the word "painter" decides what comes back: sentences about painters in general. They look plausible, which is exactly what makes this failure mode risky.

The generation step handled it correctly: given these five passages, Claude answered that the text doesn't mention Picasso.

## Why a simple distance cutoff doesn't obviously fix this

In the Vermeer run, the distance scores on the five wrong results ranged from **0.29 to 0.36**. That's the same range as the scores on results we already confirmed were correct elsewhere in this evaluation (roughly 0.30-0.45). So a passage that has nothing to do with the question can score just as "close" as one that actually answers it.

That means a rule like "throw out anything past 0.35" wouldn't reliably separate good answers from bad ones — it could just as easily cut real, correct results while still letting wrong ones through. Finding 4a in [eval_and_bugs.md](eval_and_bugs.md) adds that the range of "close" distances also shifts from query to query.

## What this means

This is a known limitation of how this kind of search works: it's built to always return whatever is *closest* to the question, even if nothing is actually close in any useful sense. It has no built-in way to say "none of this is good enough" — it can only compare the options it has to each other, not judge them against some outside standard of "relevant."

A consequence for the evaluation: at the retrieval level, a negative query can never pass. Without a threshold, retrieval always returns 5 chunks, so the harness marks q16 as FAIL by design. Whether the system behaves correctly shows up one step later, in the generated answer.

## Why this matters for the project

It's important because we want to avoid the system making things up: if it's handed five unrelated passages and asked to answer anyway, it might try to construct an answer from them instead of saying "this isn't covered in the text." In the q16 test the model refused correctly, but that currently depends on the prompt and the model, not on anything in retrieval.

## Open questions / possible next steps (not decided or built yet)

- Whether a cutoff could still work if it's tuned more carefully — e.g. by testing it against a bigger set of "nothing should match" questions to see if there's actually a point where good and bad scores separate.
- Whether some other check would work better than a distance cutoff — like checking if the generated answer actually quotes real text, or asking the model itself how confident it is.
- Testing more "nothing should match" questions beyond q16. Any new candidate should be checked against the source text first, including historical spellings — the Vermeer case shows that searching for the modern spelling isn't enough.