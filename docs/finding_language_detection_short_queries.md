# Finding: language detection is unreliable on short queries

`langdetect` (used in `lang.py` to pick what language Claude should answer in) misdetects some short, ordinary questions — not just single words Verified with repeated calls on the same input:

- `"what does Françoise cook?"` → flips between `fr` and `nl`
- `"how does he describe madeleines"` → flips between `es`, `nl`, `pt` — never `en`

Longer, less ambiguous phrase-style queries (6+ words) detected correctly and consistently in testing. `langdetect` is a statistical n-gram detector; short text just doesn't give it enough signal, and it guesses confidently instead of flagging uncertainty.

## Fix applied

Pinned `DetectorFactory.seed = 0`. This makes a given input always return the same result — it does not fix accuracy, but a _consistently_ wrong detection is testable and debuggable, where a _randomly_ wrong one wasn't.

## Open

Actually fixing this needs a real decision about the approach (e.g. only trust the detector above a certain confidence score and fall back to something else below it, use a tool built for short text instead, or reuse the French lemma pipeline already in the app as a hint) — not attempted here.
It's the same pattern as the retrieval findings in eval_and_bugs.md: a technique is being used outside the conditions it works well in (here, very short text), and instead of admitting uncertainty, it just gives a confident wrong answer.
