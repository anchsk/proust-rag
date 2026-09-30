# The Madeleine Problem

The scene of a character eating a madeleine and remembering all things past is known even to those who haven't read Proust. When thinking about queries and passages to check the retrieval, I decided to search for the madeleine.
I discovered that a query like "tell me about the madeleines" returned results very far from what I expected.

For example:

```json
[
  {
    "match": "LE BONHEUR DES MÉCHANTS COMME UN TORRENT S’ÉCOULE.",
    "context": "Après avoir regardé par le coin du rideau si Eulalie avait refermé la porte: «Les personnes flatteuses savent se faire bien venir et ramasser les pépettes; mais patience, le bon Dieu les punit toutes par un beau jour», disait-elle, avec le regard latéral et l’insinuation de Joas pensant exclusivement à Athalie quand il dit: LE BONHEUR DES MÉCHANTS COMME UN TORRENT S’ÉCOULE. Mais quand le curé était venu aussi et que sa visite interminable avait épuisé les forces de ma tante, Françoise sortait de la chambre derrière Eulalie et disait:",
    "distance": 0.5598415732383728,
    "meta": {
      "sentence_index": 0,
      "chapter_id": 1,
      "clause_index": 0,
      "fallback": false,
      "paragraph_id": 236
    }
  },
  {
    "match": "D’autres font des cures de Fontainebleau, moi je fais ma petite cure de Beauvais.",
    "context": "demandez au docteur, il vous dira que ces raisins-là me purgent. D’autres font des cures de Fontainebleau, moi je fais ma petite cure de Beauvais. Mais, monsieur Swann, vous ne partirez pas sans avoir touché les petits bronzes des dossiers.",
    "distance": 0.5883926153182983,
    "meta": {
      "chapter_id": 2,
      "clause_index": 0,
      "sentence_index": 15,
      "paragraph_id": 68,
      "fallback": false
    }
  },
  {
    "match": "pas seulement: créer.",
    "context": "Chercher? pas seulement: créer. Il est en face de quelque chose qui n’est pas encore et que seul il peut réaliser, puis faire entrer dans sa lumière.",
    "distance": 0.5901437997817993,
    "meta": {
      "clause_index": 0,
      "fallback": false,
      "paragraph_id": 45,
      "sentence_index": 22,
      "chapter_id": 1
    }
  },
  {
    "match": "dit Forcheville étonné.",
    "context": "— C’est curieux! dit Forcheville étonné. Un genre d’esprit comme celui de Brichot aurait été tenu pour stupidité pure dans la coterie où Swann avait passé sa jeunesse, bien qu’il soit compatible avec une intelligence réelle.",
    "distance": 0.6148518919944763,
    "meta": {
      "paragraph_id": 212,
      "sentence_index": 1,
      "chapter_id": 2,
      "fallback": false,
      "clause_index": 0
    }
  },
  {
    "match": "Lis donc ces proses lyriques, et si le gigantesque assembleur de rythmes qui a écrit Bhagavat et le Levrier de Magnus a dit vrai, par Apollôn, tu goûteras, cher maître, les joies nectaréennes de l’Olympos.»",
    "context": "Il tient, m’a-t-on dit, l’auteur, le sieur Bergotte, pour un coco des plus subtils; et bien qu’il fasse preuve, des fois, de mansuétudes assez mal explicables, sa parole est pour moi oracle delphique. Lis donc ces proses lyriques, et si le gigantesque assembleur de rythmes qui a écrit Bhagavat et le Levrier de Magnus a dit vrai, par Apollôn, tu goûteras, cher maître, les joies nectaréennes de l’Olympos.» C’est sur un ton sarcastique qu’il m’avait demandé de l’appeler «cher maître» et qu’il m’appelait lui-même ainsi.",
    "distance": 0.6212009191513062,
    "meta": {
      "sentence_index": 8,
      "clause_index": 0,
      "chapter_id": 1,
      "fallback": false,
      "paragraph_id": 163
    }
  }
]
```

None of these passages is relevant. Searching for the bare word "madeleine" didn't give good results either. Chroma returns its least-bad options because it has no way to return "nothing relevant" (see [finding_negative_case_no_threshold.md](finding_negative_case_no_threshold.md)).

The distances here are high (0.56 and above), but later testing showed that distance alone isn't a reliable signal: irrelevant results can score as low as relevant ones, and the range shifts from query to query (see findings 4a and 5 in [eval_and_bugs.md](eval_and_bugs.md)).

## Figuring out why

First I checked whether the expected chunks were indexed at all. In the CSV with all the text prepared for indexing, I searched for "madeleine", and it was there.
Querying ChromaDB for the exact passage ID returned the passage:

```py
result = collection.get(ids=["ch1_p45_s2_c0"], include=["embeddings"])
print(result["embeddings"])
```

The embedding is a real vector. So the data was there, but it wasn't being retrieved.

Then I checked the actual similarity between that chunk and the query:

```py
madeleine_emb = collection.get(ids=["ch1_p45_s2_c0"], include=["embeddings"])["embeddings"][0]
query_emb = multilingual_ef(["madeleine"])[0]

import numpy as np
cos_sim = np.dot(madeleine_emb, query_emb) / (np.linalg.norm(madeleine_emb) * np.linalg.norm(query_emb))
print(cos_sim)
```

The result is 0.2008: very low for a passage that contains the query word itself.

## The reason

The embedding model (multilingual MiniLM) represents a whole sentence as one vector, based on statistical patterns learned in training. It doesn't do substring matching, and it has no knowledge that "madeleine" is significant in this book. A one-word query and a long sentence that happens to contain that word don't end up close in vector space: the sentence's overall content outweighs the single shared word. This is a general limitation of dense embedding search, not a bug in this project.

## The solution: hybrid search (implemented)

This showed that pure vector search can miss exact keyword matches, so I added a second, exact-term layer alongside the semantic one:

1. **A lemma index**, built in `proust-pipeline` with spaCy (`fr_core_news_lg`): for each noun and proper noun in the text, its dictionary form (lemma) maps to the chunks it appears in. "madeleines" and "madeleine" both map to `madeleine`.
2. **Routing by rarity** (`classify_intent`): if a query contains a noun or name that appears in 50 chunks or fewer, lemma search runs in addition to semantic search. Very common words ("Swann", "Françoise") are skipped, since an exact match on them isn't informative.
3. **Merging** (`merge_results`): results from both searches are combined into one list, without duplicates, before being sent to Claude.

## Result

The same query now returns the madeleine passages, including the one that semantic search alone missed (`ch1_p45_s2_c0`):

```py
arr1 = lemma_search_with_context('madeleine', limit=10)
print('arr1', arr1)
arr2 = search_db('madeleine', limit=5)
print([x["meta"]["chunk_id"] for x in merge_results(arr1, arr2)])
```

```
['ch1_p45_s2_c0', 'ch1_p49_s1_c0', 'ch1_p50_s0_c0', 'ch3_p52_s1_c0', 'ch1_p49_s2_c0', 'ch1_p55_s6_c0', 'ch1_p119_s1_c0', 'ch1_p45_s3_c0', 'ch1_p345_s1_c0', 'ch1_p45_s22_c0', 'ch2_p68_s15_c0', 'ch1_p275_s6_c0', 'ch2_p212_s1_c0']
```

The first eight are lemma matches: every chunk containing *madeleine*. Since the query is a single lemma, they tie on score, and their order changes between runs (see the MRR note in [eval_and_bugs.md](eval_and_bugs.md)). Two of them aren't about the cake at all: "la Madeleine" (the Paris church and district, `ch3_p52_s1_c0`) and the actress Madeleine Brohan (`ch1_p119_s1_c0`). Exact-term search matches the word, not its meaning. The last five are the semantic results, which include the same irrelevant passages as before; the merge places the exact matches ahead of them rather than removing them.

The madeleine scene is also part of the eval set (`q05` in `eval_set.json`).

## Limits of the solution

- Exact-term search finds every occurrence of a **specific word**, but not a **category**: "find all mentions of flowers" doesn't work, because the lemma index doesn't know that *rose*, *lilas* and *aubépine* are flowers.
- It only covers nouns and proper names, so a query whose only specific word is a verb relies on semantic search alone.
- Names in historical spelling are only found in that spelling: "Vermeer" misses Proust's "Ver Meer" (see finding 7 in [eval_and_bugs.md](eval_and_bugs.md)).
- It matches words, not meanings: a search for *madeleine* also returns the Paris church and an actress named Madeleine.