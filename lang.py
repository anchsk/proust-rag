from langdetect import detect

questions = [
    "Come è descritto il giardino della nonna?",
    "Что говорится о цветах в саду",
    "How are the flowers described?",
    "Comment décrit-il le jardin?",
    "fleurs dans le jardin",
    "цветы",
    "fleurs",
    "プルーストは庭の花について何と言っていますか？"
]

for q in questions:
    print(f"{q!r} {detect(q)}")

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
