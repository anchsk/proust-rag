import collections

import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
from extract_lemmas import extract_lemmas

CHROMA_PATH = "./chroma_db"

settings = {"freq_threshold": 50, # lemmas with lower frequency are considered unique
            "lemma_limit": 50,
            "db_limit": 5,
            "window": 0}

multilingual_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(
    "proust_chunks", embedding_function=multilingual_ef)

# result = collection.get(where_document={"$contains": "Vermeer"})
# print(result)


def load_lemma_index(path):
    df = pd.read_csv(path)
    index = {}
    for _, row in df.iterrows():
        index.setdefault(row["lemma"], []).append(row["chunk_id"])
    return index


# fast in-memory look up built on each run
lemma_index = load_lemma_index("data/lemma_index.csv")

# print(lemma_index.get("balbec"))
# print(len(lemma_index.get("balbec", [])))


def load_chunk_metadata(path):
    df = pd.read_csv(path)
    return df.set_index("chunk_id").to_dict("index")


chunk_metadata = load_chunk_metadata("data/proust_chunks_merged.csv")


def lemma_search(query_text, limit):
    lemmas = extract_lemmas(query_text)

    count = collections.Counter()
    # count_n = collections.Counter(dict.fromkeys(lemmas, 0))

    for lemma in lemmas:
        lemma_list = lemma_index.get(lemma, [])
        df = len(lemma_list)
        lemma_ids = set(lemma_list)
        # count_n[lemma] += len(lemma_index.get(lemma, []))
        for x in lemma_ids:
            count[x] += 1/df  # weighted score

    # match a rare informative item
    most_common = count.most_common()
    chunk_ids = [x[0] for x in most_common]
    # print("DEBUG count", count.most_common(10))
    return list(chunk_ids)[:limit]


def _sorted_chunks(result):
    return sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda x: (x[0]["sentence_index"], x[0]["clause_index"])
    )


def get_context(chapter_id, paragraph_id, sentence_index, window=1):
    before, after = [], []

    # --- look back into previous paragraph if window goes negative ---
    deficit_before = max(0, window - sentence_index)
    if deficit_before > 0 and paragraph_id > 0:
        prev = collection.get(where={"$and": [
            {"chapter_id": chapter_id},
            {"paragraph_id": paragraph_id - 1},
        ]})
        prev_combined = _sorted_chunks(prev)
        if prev_combined:
            max_idx = prev_combined[-1][0]["sentence_index"]
            cutoff = max_idx - deficit_before + 1
            before = [doc for meta,
                      doc in prev_combined if meta["sentence_index"] >= cutoff]

    # --- current paragraph, normal window ---
    current = collection.get(where={"$and": [
        {"chapter_id": chapter_id},
        {"paragraph_id": paragraph_id},
        {"sentence_index": {"$gte": max(0, sentence_index - window)}},
        {"sentence_index": {"$lte": sentence_index + window}},
    ]})
    current_combined = _sorted_chunks(current)
    current_texts = [doc for _, doc in current_combined]

    # figure out how many sentences we actually got from the current paragraph
    # to know if we still owe sentences from the next paragraph
    max_current_idx = max((m["sentence_index"]
                          for m, _ in current_combined), default=sentence_index)
    deficit_after = max(0, (sentence_index + window) - max_current_idx)

    # --- look forward into next paragraph if window overruns ---
    if deficit_after > 0:
        nxt = collection.get(where={"$and": [
            {"chapter_id": chapter_id},
            {"paragraph_id": paragraph_id + 1},
        ]})
        nxt_combined = _sorted_chunks(nxt)
        if nxt_combined:
            cutoff = deficit_after - 1  # 0-indexed: take the first `deficit_after` sentences
            after = [doc for meta,
                     doc in nxt_combined if meta["sentence_index"] <= cutoff]

    return " ".join(before + current_texts + after)


def search_db(query, limit=10, window=1):
    results = collection.query(query_texts=[query], n_results=limit)
    output = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        context = get_context(
            meta["chapter_id"], meta["paragraph_id"], meta["sentence_index"], window)
        output.append({"match": doc, "context": context,
                      "distance": dist, "meta": meta})
       # print(f"({dist:.3f})\nMatch: {doc}\nContext: {context}\n")

    return output


def lemma_search_with_context(query_text, limit, window=1):
    chunk_ids = lemma_search(query_text, limit)
    # print('chunk_ids', chunk_ids)
    output = []
    for chunk_id in chunk_ids:
        meta = chunk_metadata[chunk_id]
        context = get_context(
            meta["chapter_id"], meta["paragraph_id"], meta["sentence_index"], window)
        output.append({"match": meta.get("text", ""),
                      "context": context, "meta": meta})
    return output


def format_chunk_id(chapter_id, paragraph_id, sentence_index, clause_index):
    return f"ch{chapter_id}_p{paragraph_id}_s{sentence_index}_c{clause_index}"


def merge_results(arr1, arr2):
    merged = {}
    for item in arr1 + arr2:
        m = item["meta"]
        key = format_chunk_id(
            m["chapter_id"], m["paragraph_id"], m["sentence_index"], m["clause_index"])
        if key not in merged:
            item["meta"]["chunk_id"] = key
            merged[key] = item
    return list(merged.values())


def retrieve(query):
    intent = classify_intent(query, freq_threshold=settings["freq_threshold"])
    semantic_results = search_db(query, limit=settings["db_limit"])

    lemma_results = []
    if intent == "both":
        lemma_results = lemma_search_with_context(
            query, window=0, limit=settings["lemma_limit"])

    return merge_results(lemma_results, semantic_results)


def classify_intent(query_text, freq_threshold=settings["freq_threshold"]):
    lemmas = extract_lemmas(query_text)
    # print(f"DEBUG lemma_index size: {len(lemma_index)}")
    # print(f"DEBUG lemmas: {lemmas}")
    # specific_lemmas = [
    #     l for l in lemmas
    #     if l in lemma_index and len(lemma_index[l]) <= freq_threshold
    # ]

    # debugging:
    specific_lemmas = []
    for l in lemmas:
        in_index = l in lemma_index
        count = len(lemma_index[l]) if in_index else None
        # print(f"DEBUG checking '{l}': in_index={in_index}, count={count}, threshold={freq_threshold}")
        if in_index and count <= freq_threshold:
            specific_lemmas.append(l)
    # print(f"DEBUG specific_lemmas: {specific_lemmas}")

    if specific_lemmas:
        return "both"
    return "semantic"


# arr1 = lemma_search_with_context('madeleine')
# arr2 = search_db('madeleine', n_results=5)

# print([x["meta"]["chunk_id"] for x in merge_results(arr1,arr2)])

# ch1_p50_s0_c0
# ch1_p45_s3_c0
# ch1_p119_s1_c0
# ch1_p49_s1_c0
# ch1_p49_s2_c0
# ch1_p45_s2_c0
# ch3_p52_s1_c0
# ch1_p55_s6_c0
# ch1_p345_s1_c0
# ch1_p45_s22_c0
# ch2_p68_s15_c0
# ch1_p275_s6_c0
# ch2_p212_s1_c0
# ['ch1_p50_s0_c0', 'ch1_p45_s3_c0', 'ch1_p119_s1_c0', 'ch1_p49_s1_c0', 'ch1_p49_s2_c0', 'ch1_p45_s2_c0', 'ch3_p52_s1_c0', 'ch1_p55_s6_c0', 'ch1_p345_s1_c0', 'ch1_p45_s22_c0', 'ch2_p68_s15_c0', 'ch1_p275_s6_c0', 'ch2_p212_s1_c0']
