import pytest
from extract_lemmas import extract_lemmas

@pytest.mark.parametrize("text, expected", [
    ("Mme Swann", ["mme", "swann"]),
    ("how does he describe Balbec church", ["doe", "balbec"]),
    ("Odette et Swann s'embrassent", ["odette", "swann"]),
    ("faire catleya", ["catleya"])
])
def test_extract_lemmas(text, expected):
    assert extract_lemmas(text) == expected
    
    
def test_extract_lemmas_keeps_names_in_non_french_query():
    assert "balbec" in extract_lemmas("how does he describe Balbec church")