import pytest
from search import classify_intent

@pytest.mark.parametrize("query,expected", [
    ("madeleine", "both"),
    ("what does Françoise cook?", "semantic"),
    ("how does he describe Balbec church", "both"),
    ("Mme Swann", "semantic"),
    ("Swann", "semantic"),
    ("pain d'épices Swann", "both"),
    ("what does the narrator feel about Françoise?", "semantic"),
    ("how does the narrator feel about his mother", "semantic")
])
def test_classify_intent(query, expected):
    assert classify_intent(query) == expected
    
    
    