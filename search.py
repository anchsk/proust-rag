import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "./chroma_db"


multilingual_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection("proust_chunks", embedding_function=multilingual_ef)


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
            before = [doc for meta, doc in prev_combined if meta["sentence_index"] >= cutoff]

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
    max_current_idx = max((m["sentence_index"] for m, _ in current_combined), default=sentence_index)
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
            after = [doc for meta, doc in nxt_combined if meta["sentence_index"] <= cutoff]

    return " ".join(before + current_texts + after)

def search(query, n_results=10, window=1):
    results = collection.query(query_texts=[query], n_results=n_results)
    output = []
    for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        context = get_context(meta["chapter_id"], meta["paragraph_id"], meta["sentence_index"], window)
        output.append({"match": doc, "context": context, "distance": dist, "meta": meta})
       # print(f"({dist:.3f})\nMatch: {doc}\nContext: {context}\n")

    return output
