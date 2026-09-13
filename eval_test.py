import collections
from pathlib import Path
import json

from search import classify_intent, lemma_search_with_context, merge_results, search_db, settings
json_path = Path(__file__).with_name("eval_set.json")

with json_path.open("r", encoding="utf-8") as f:
    eval_set = json.load(f)

# recall_scores = []
# mrr_scores = []

regular_cases, negative_cases = [c for c in eval_set if c["type"] != "negative"], [
    c for c in eval_set if c["type"] == "negative"]

recall_by_type = collections.defaultdict(list)
mrr_by_type = collections.defaultdict(list)
coverage_by_type = collections.defaultdict(list)

# order of arrays is important here


def reciprocal_rank(found_ids, expected_ids):
    reciprocal_rank = 0
    for i, el in enumerate(found_ids):
        if el in expected_ids:
            reciprocal_rank = 1 / (i + 1)
            break
    return reciprocal_rank

# order is irrelevant


def hit_at_k(found_ids, expected_ids):
    overlap = set(found_ids) & set(expected_ids)
    return overlap


def run_pipeline(query):
    intent = classify_intent(query, freq_threshold=settings["freq_threshold"])
    semantic_results = search_db(query, limit=5)

    lemma_results = []
    if intent == "both":
        lemma_results = lemma_search_with_context(
            query, window=0, limit=settings["lemma_limit"])

    results = merge_results(lemma_results, semantic_results)
    chunk_id_list = [r["meta"]["chunk_id"] for r in results]
    return chunk_id_list


for case in regular_cases:
    query = case["query"]

    chunk_id_list = run_pipeline(query)

    rank = reciprocal_rank(chunk_id_list, case["expected_chunk_ids"])
    # mrr_scores.append(reciprocal_rank)
    mrr_by_type[case["type"]].append(rank)

    overlap = hit_at_k(chunk_id_list, case["expected_chunk_ids"])
    # recall_scores.append(1 if overlap else 0)
    recall_by_type[case["type"]].append(1 if overlap else 0)
    coverage = len(overlap) / len(case["expected_chunk_ids"])
    coverage_by_type[case["type"]].append(coverage)


for case in negative_cases:
    chunk_id_list = run_pipeline(case["query"])
    status = "PASS (no results)" if not chunk_id_list else f"CHECK (returned {chunk_id_list})"
    print(f"{case['id']}: {status}")

# overall_mrr_score = sum(mrr_scores) / len(mrr_scores)
# overall_recall_score = sum(recall_scores) / len(recall_scores)
print("RECALL: ")
for type_name in sorted(recall_by_type):
    scores = recall_by_type[type_name]
    print(type_name, sum(scores) / len(scores))

print("MRR: ")
for type_name in sorted(mrr_by_type):
    scores = mrr_by_type[type_name]
    print(type_name, sum(scores) / len(scores))
