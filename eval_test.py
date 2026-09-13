import collections
from pathlib import Path
import json

from search import classify_intent, lemma_search_with_context, merge_results, search_db

json_path = Path(__file__).with_name("eval_set.json")

print("before load")
with json_path.open("r", encoding="utf-8") as f:
    eval_set = json.load(f)
    # recall_scores = []
    # mrr_scores = []
    
    recall_by_type = collections.defaultdict(list)
    mrr_by_type = collections.defaultdict(list)
    
    for item in eval_set:
        query = item["query"]
    
        intent = classify_intent(query, freq_threshold=50)
        semantic_results = search_db(query, limit=5)
    
        lemma_results = []
        if intent == "both":
            lemma_results = lemma_search_with_context(query, window=0, limit=50)
    
        results = merge_results(lemma_results, semantic_results)
        chunk_id_list = [r["meta"]["chunk_id"] for r in results]
        
        reciprocal_rank = 0
        for i, el in enumerate(chunk_id_list):
            if el in item["expected_chunk_ids"]:
                reciprocal_rank = 1 / (i + 1)
                break
        # mrr_scores.append(reciprocal_rank)
        mrr_by_type[item["type"]].append(reciprocal_rank)

                
        
        a = collections.Counter(item["expected_chunk_ids"])
        b = collections.Counter(chunk_id_list)

        overlap = list((a & b).elements())
        # recall_scores.append(1 if overlap else 0)
        print('question: ', query, 'overlap: ', overlap)
        recall_by_type[item["type"]].append(1 if overlap else 0)
        
    # overall_mrr_score = sum(mrr_scores) / len(mrr_scores)    
    # overall_recall_score = sum(recall_scores) / len(recall_scores)

    print("RECALL: ")
    for type_name, scores in recall_by_type.items():
        print(type_name, sum(scores) / len(scores))
        
    print("MRR: ")
    for type_name, scores in mrr_by_type.items():
        print(type_name, sum(scores) / len(scores))


        
    
print("after load")
