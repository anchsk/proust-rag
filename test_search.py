from search import retrieve


def test_search_cross_lingual_francoise_cook():
    results = retrieve("cosa cucinava Françoise?")
    assert results[0]["meta"]["chunk_id"] == "ch1_p261_s0_c0"
