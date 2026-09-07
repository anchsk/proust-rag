# The Madeleine Problem (WIP)

The scene of a personage eating a madeleine and remembering all things past is known even to those who haven't read Proust. When thinking about queries and passages to check the retrieval, I decided to search for the madeleine.
I discovered that the query of type "tell me about the madeleines" returned the results that were very far from what I expected it to be.

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

None of these passages is good. The distances are high: the closest one is 0.559 and it returns an irrelevant chunk of text. Neither searching for "madeleine" provides a good result. Chroma is returning its least-bad option because it can't return "nothing relevant".

## Figuring out why

I've checked if the chunks I expected were indexed at all. In the csv with all the text prepared to be indexed, I've searched for "madeleine" and it was there.
Quering ChromaDB for the exact passage id, returned the passage.

```py
result = collection.get(ids=["ch1_p45_s2_c0"], include=["embeddings"])
print(result["embeddings"])
```

The embeddings is a real vector. So the data was there, it was just not appearing.

Checking for the actual similarity between the specific chunk and the query:

```py
madeleine_emb = collection.get(ids=["ch1_p45_s2_c0"], include=["embeddings"])["embeddings"][0]
query_emb = multilingual_ef(["madeleine"])[0]

import numpy as np
cos_sim = np.dot(madeleine_emb, query_emb) / (np.linalg.norm(madeleine_emb) * np.linalg.norm(query_emb))
print(cos_sim)
```

The result is 0.2007715439029371 and it is very low.

## The reason

Multilingual MiniLM is doing pattern-matching on statistical co-occurence patterns. It does not reason about the text and it doesn't have a deep knowledge to recognize "madeleine" as significant.
In this case, the query is short and doesn't sit close in vector space because the model is comparing the chunk meaning, not doing substring matching. This is a documented limitation of sentence-transformer models. For the model, the sentence's dominant semantic content overweighs the literal keyword match.

## The conclusion

After discovering this limitation, there were two things to consider. First, pure vector search can miss keyword matches. And another thing I had in mind it's to be able to make exhaustive queries of type "find all mentions of flowers".
This can be achieved with hybrid search. Keyword queries should work alongside semantic ones.

Roughly the plan is: index for keyword/exact search too, implement intent classification (route to keyword, semantic, or both)/
