from langdetect import detect, DetectorFactory

DetectorFactory.seed = 0  # langdetect is otherwise nondeterministic on short/ambiguous text

# questions = [
#     "Come è descritto il giardino della nonna?",
#     "Что говорится о цветах в саду",
#     "How are the flowers described?",
#     "Comment décrit-il le jardin?",
#     "fleurs dans le jardin",
#     "цветы",
#     "fleurs",
#     "プルーストは庭の花について何と言っていますか？"
# ]

# for q in questions:
#     print(f"{q!r} {detect(q)}")

def detect_language(text):
    if not text:
        return 'en'
    return detect(text)

# 'Come è descritto il giardino della nonna?' it
# 'Что говорится о цветах в саду' ru
# 'How are the flowers described?' en
# 'Comment décrit-il le jardin?' fr
# 'fleurs dans le jardin' fr
# 'цветы' ru
# 'fleurs' fr
# 'プルーストは庭の花について何と言っていますか？' ja


# madeleine -> ['et', 'et', 'et', 'et', 'de', 'et', 'et', 'et']   # Estonian / German (?!)
# Balbec    -> ['de', 'de', 'de', 'de', 'de', 'de', 'de', 'de']   # German, every time
# Combray   -> ['es', 'es', 'es', 'es', 'es', 'es', 'es', 'es']   # Spanish, every time
# fleurs    -> ['fr', 'fr', 'fr', 'fr', 'fr', 'fr', 'fr', 'fr']   # correct