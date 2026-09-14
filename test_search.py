from main import settings
from search import classify_intent, search_db, merge_results, lemma_search_with_context
# q = "what does the narrator feel about Françoise?"
q = "cosa cucinava Françoise?" 
def run_pipeline(query):
    intent = classify_intent(query, freq_threshold=settings["freq_threshold"])
    semantic_results = search_db(query, settings["db_limit"])

    lemma_results = []
    if intent == "both":
        lemma_results = lemma_search_with_context(
            query, window=0, limit=settings["lemma_limit"])
    print("lemma results: ", [lemma_results["meta"]["chunk_id"] for r in lemma_results])

    results = merge_results(lemma_results, semantic_results)
    chunk_id_list = [r["meta"]["chunk_id"] for r in results]
    print([(r["meta"]["chunk_id"], r["distance"]) for r in results])
    return chunk_id_list
results = run_pipeline(q)