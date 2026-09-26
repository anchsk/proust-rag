# Finding: the system always returns results, even when there's nothing relevant

## Summary
There's no way for the system to say "I don't have an answer to this." Semantic search always hands back its 5 closest matches, even for a question about something that isn't in the text at all. And the distance scores on those bad matches don't look meaningfully different from the scores on good matches. So, just cutting off results past a certain distance isn't a clean fix.

## Test case
Query: *"What does the narrator say about the painter Vermeer?"*
Vermeer isn't mentioned anywhere in chapters 1-3 (Swann's Way).

What should happen: no chunks returned, or some clear signal that nothing relevant was found.

What actually happened:
```
q14: FAIL: returned ['ch2_p240_s1_c0', 'ch2_p341_s0_c0', 'ch2_p45_s9_c0', 'ch2_p2_s8_c0', 'ch2_p293_s1_c0']
```
Five chunks came back, with nothing marking them as unrelated to the question.

## Why a simple distance cutoff doesn't obviously fix this

The distance scores on these five wrong results ranged from **0.29 to 0.36**. That's the same range as the scores on results we already confirmed were correct elsewhere in this evaluation (roughly 0.30-0.45). So a passage that has nothing to do with the question can score just as "close" as one that actually answers it.

That means a rule like "throw out anything past 0.35" wouldn't reliably separate good answers from bad ones — it could just as easily cut real, correct results while still letting wrong ones through.

## What this means

This is a known limitation of how this kind of search works: it's built to always return whatever is *closest* to the question, even if nothing is actually close in any useful sense. It has no built-in way to say "none of this is good enough" — it can only compare the options it has to each other, not judge them against some outside standard of "relevant."

So, it's just a general weakness of this search method that hasn't been worked around yet here.

## Why this matters for the project

It's important because we want to avoid the system making things up: if it's handed five unrelated passages and asked to answer anyway, it might try to construct an answer from them instead of saying "this isn't covered in the text." This test case gives something concrete to work from for that problem, instead of just a vague goal.

## Open questions / possible next steps (not decided or built yet)

- Whether a cutoff could still work if it's tuned more carefully — e.g. by testing it against a bigger set of "nothing should match" questions to see if there's actually a point where good and bad scores separate.
- Whether some other check would work better than a distance cutoff — like checking if the generated answer actually quotes real text, or asking the model itself how confident it is.
- Testing more "nothing should match" questions beyond just this one, to see if the 0.29-0.36 range shows up again or if Vermeer just happened to be an unusually close case.