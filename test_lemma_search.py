import pytest
from search import lemma_search


@pytest.mark.parametrize("query, expected", [
    ("pain d'épices Swann", "ch3_p18_s4_c0")
])

def test_lemma_search(query, expected):
    assert lemma_search(query, limit=50)[0] == expected