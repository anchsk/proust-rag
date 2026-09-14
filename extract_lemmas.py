import spacy

nlp = spacy.load('fr_core_news_lg')

def extract_lemmas(text):
    doc = nlp(text)
    lemmas = []
    
    for sent in doc.sents:
        for token in sent:
            if not token.is_alpha or token.is_stop:
                continue
            if not token.pos_ in ["NOUN", "PROPN"]:
                continue
            lemma = token.lemma_.lower()
            lemmas.append(lemma)
            
    return lemmas
