import collections
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.utils import embedding_functions
import pandas as pd
from extract_lemmas import extract_lemmas

CHROMA_PATH = "./chroma_db"


@dataclass(frozen=True)
class Settings:
    freq_threshold: int = 50  # lemmas with lower frequency are considered unique
    lemma_limit: int = 50
    db_limit: int = 5


settings = Settings()


@lru_cache
def get_embedding_function():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )


@lru_cache
def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_collection(
        "proust_chunks", embedding_function=get_embedding_function())


def load_lemma_index(path):
    df = pd.read_csv(path)
    index = {}
    for _, row in df.iterrows():
        index.setdefault(row["lemma"], []).append(row["chunk_id"])
    return index


@lru_cache
def get_lemma_index():
    return load_lemma_index("data/lemma_index.csv")


def load_chunk_metadata(path):
    df = pd.read_csv(path)
    return df.set_index("chunk_id").to_dict("index")


@lru_cache
def get_chunk_metadata():
    return load_chunk_metadata("data/proust_chunks_merged.csv")

def is_specific(lemma, freq_threshold):
    lemma_index = get_lemma_index()
    return lemma in lemma_index and len(lemma_index[lemma]) <= freq_threshold



def lemma_search(query_text, limit, freq_threshold=settings.freq_threshold):
    lemmas = extract_lemmas(query_text)
    lemma_index = get_lemma_index()

    candidates = set()             # who is allowed in: chunks with a rare word
    count = collections.Counter()  # points: every word counts

    for lemma in lemmas:
        lemma_list = lemma_index.get(lemma, [])
        lemma_ids = set(lemma_list)

        if is_specific(lemma, freq_threshold):
            candidates.update(lemma_ids)

        doc_freq = len(lemma_list)
        for x in lemma_ids:
            count[x] += 1 / doc_freq  # rare words give more points

    # keep only candidates; common words only reorder them, never add chunks
    chunk_ids = [chunk_id for chunk_id, _ in count.most_common() if chunk_id in candidates]
    return chunk_ids[:limit]

def _sorted_chunks(result):
    return sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda x: (x[0]["sentence_index"], x[0]["clause_index"])
    )


def _fetch_paragraph_sorted(chapter_id, paragraph_id, extra_where=None):
    where_clauses = [{"chapter_id": chapter_id}, {"paragraph_id": paragraph_id}]
    if extra_where:
        where_clauses.extend(extra_where)
    result = get_collection().get(where={"$and": where_clauses})
    return _sorted_chunks(result)


def get_context(chapter_id, paragraph_id, sentence_index, window=1):
    before, after = [], []

    # --- look back into previous paragraph if window goes negative ---
    deficit_before = max(0, window - sentence_index)
    if deficit_before > 0 and paragraph_id > 0:
        prev_combined = _fetch_paragraph_sorted(chapter_id, paragraph_id - 1)
        if prev_combined:
            max_idx = prev_combined[-1][0]["sentence_index"]
            cutoff = max_idx - deficit_before + 1
            before = [doc for meta,
                      doc in prev_combined if meta["sentence_index"] >= cutoff]

    # --- current paragraph, normal window ---
    current_combined = _fetch_paragraph_sorted(chapter_id, paragraph_id, extra_where=[
        {"sentence_index": {"$gte": max(0, sentence_index - window)}},
        {"sentence_index": {"$lte": sentence_index + window}},
    ])
    current_texts = [doc for _, doc in current_combined]

    # figure out how many sentences we actually got from the current paragraph
    # to know if we still owe sentences from the next paragraph
    max_current_idx = max((m["sentence_index"]
                          for m, _ in current_combined), default=sentence_index)
    deficit_after = max(0, (sentence_index + window) - max_current_idx)

    # --- look forward into next paragraph if window overruns ---
    if deficit_after > 0:
        nxt_combined = _fetch_paragraph_sorted(chapter_id, paragraph_id + 1)
        if nxt_combined:
            cutoff = deficit_after - 1  # 0-indexed: take the first `deficit_after` sentences
            after = [doc for meta,
                     doc in nxt_combined if meta["sentence_index"] <= cutoff]

    return " ".join(before + current_texts + after)


def search_db(query_text, limit, window=1):
    results = get_collection().query(query_texts=[query_text], n_results=limit)
    output = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        context = get_context(
            meta["chapter_id"], meta["paragraph_id"], meta["sentence_index"], window)
        output.append({"match": doc, "context": context,
                      "distance": dist, "meta": meta})
    return output


def lemma_search_with_context(query_text, limit, window=1):
    chunk_ids = lemma_search(query_text, limit)
    output = []
    for chunk_id in chunk_ids:
        meta = get_chunk_metadata()[chunk_id]
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
    intent = classify_intent(query, freq_threshold=settings.freq_threshold)
    semantic_results = search_db(query, limit=settings.db_limit)

    lemma_results = []
    if intent == "both":
        lemma_results = lemma_search_with_context(
            query, window=0, limit=settings.lemma_limit)

    return merge_results(lemma_results, semantic_results)


def classify_intent(query_text, freq_threshold=settings.freq_threshold):
    lemmas = extract_lemmas(query_text)
    
    specific_lemmas = [lemma for lemma in lemmas if is_specific(lemma, freq_threshold)]

    if specific_lemmas:
        return "both"
    return "semantic"


