from search import classify_intent


test_cases = [
    ("madeleine", "both"),                          # rare, specific term
    ("what does Françoise cook?", "semantic"),       # frequent name, no exact anchor
    ("how does he describe Balbec church", "both"),  # specific place name
    ("how does the narrator feel about his mother", "semantic"),  # thematic, no fixed term
    ("pain d'épices Swann", "both")
]

for query, expected in test_cases:
    result = classify_intent(query)
    status = "PASS" if result == expected else "FAIL"
    print(f"{status}: '{query}' -> got '{result}', expected '{expected}'")
    
# PASS: 'madeleine' -> got 'both', expected 'both'
# PASS: 'what does Françoise cook?' -> got 'semantic', expected 'semantic'
# FAIL: 'how does he describe Balbec church' -> got 'semantic', expected 'both'
# PASS: 'how does the narrator feel about his mother' -> got 'semantic', expected 'semantic'