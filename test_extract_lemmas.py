import pytest
from extract_lemmas import extract_lemmas

@pytest.mark.parametrize("text, expected", [
    ("Mme Swann", ["mme", "swann"]),
    ("how does he describe Balbec church", ["doe", "balbec"]),
])
def test_extract_lemmas(text, expected):
    assert extract_lemmas(text) == expected
    